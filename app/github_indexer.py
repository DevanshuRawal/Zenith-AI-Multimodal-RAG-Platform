import base64
import logging
import re
from typing import Any
from urllib.parse import quote

import requests

from app.config import (
    GITHUB_API_TOKEN,
    GITHUB_MAX_FILE_BYTES,
    GITHUB_MAX_FILES,
    MAX_CHUNK_SIZE,
    CHUNK_OVERLAP,
)
from app.ingestion import chunk_text_with_locations

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".py",
    ".md",
    ".rst",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
}
EXCLUDED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "__pycache__",
}
OWNER_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
REPOSITORY_PATTERN = re.compile(r"^(?!\.{1,2}$)[A-Za-z0-9_.-]{1,100}$")


class GitHubRepositoryError(RuntimeError):
    pass


def validate_repository_name(owner: str, repository: str):
    if not OWNER_PATTERN.fullmatch(owner) or not REPOSITORY_PATTERN.fullmatch(
        repository
    ):
        raise ValueError("Invalid GitHub owner or repository name.")


class GitHubClient:
    def __init__(
        self,
        token: str | None = GITHUB_API_TOKEN,
        session: requests.Session | None = None,
    ):
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def _get_json(self, url: str, params: dict | None = None):
        response = self.session.get(url, params=params, timeout=(5, 30))
        if response.status_code == 404:
            raise GitHubRepositoryError(
                "Repository or requested GitHub resource was not found."
            )
        if response.status_code == 403:
            raise GitHubRepositoryError(
                "GitHub denied access or its API rate limit was reached."
            )
        response.raise_for_status()
        return response.json()

    def get_default_branch(self, owner: str, repository: str) -> str:
        url = f"https://api.github.com/repos/{quote(owner)}/{quote(repository)}"
        result = self._get_json(url)
        branch = result.get("default_branch")
        if not isinstance(branch, str) or not branch:
            raise GitHubRepositoryError("GitHub repository has no default branch.")
        return branch

    def list_files(self, owner: str, repository: str, branch: str) -> list[dict]:
        url = (
            f"https://api.github.com/repos/{quote(owner)}/{quote(repository)}"
            f"/git/trees/{quote(branch, safe='')}"
        )
        result = self._get_json(url, params={"recursive": "1"})
        if result.get("truncated"):
            raise GitHubRepositoryError(
                "GitHub returned a truncated repository tree; indexing was stopped."
            )
        return [
            item
            for item in result.get("tree", [])
            if item.get("type") == "blob"
        ]

    def get_file_content(self, owner: str, repository: str, sha: str) -> str:
        url = (
            f"https://api.github.com/repos/{quote(owner)}/{quote(repository)}"
            f"/git/blobs/{quote(sha, safe='')}"
        )
        result = self._get_json(url)
        if result.get("encoding") != "base64" or not isinstance(
            result.get("content"), str
        ):
            raise GitHubRepositoryError("GitHub returned an unsupported blob format.")
        try:
            return base64.b64decode(result["content"], validate=False).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise GitHubRepositoryError("Repository file is not valid UTF-8 text.") from exc


class GitHubRepositoryIndexer:
    def __init__(
        self,
        store: Any,
        github_client: Any | None = None,
        max_file_bytes: int = GITHUB_MAX_FILE_BYTES,
        max_files: int = GITHUB_MAX_FILES,
    ):
        if max_file_bytes <= 0 or max_files <= 0:
            raise ValueError("GitHub indexing limits must be positive.")
        self.store = store
        self.github_client = github_client or GitHubClient()
        self.max_file_bytes = max_file_bytes
        self.max_files = max_files

    def index(self, owner: str, repository: str) -> dict:
        validate_repository_name(owner, repository)
        branch = self.github_client.get_default_branch(owner, repository)
        tree = self.github_client.list_files(owner, repository, branch)
        files_seen = 0
        files_indexed = 0
        chunks_created = 0

        for item in tree:
            if files_seen >= self.max_files:
                logger.info(
                    "GitHub indexing file limit reached for %s/%s",
                    owner,
                    repository,
                )
                break
            files_seen += 1
            path = item.get("path", "")
            sha = item.get("sha", "")
            if not self._is_supported_path(path) or not sha:
                continue
            size = item.get("size")
            if not isinstance(size, int) or size < 0:
                logger.warning("Skipping GitHub blob without a valid size: %s", path)
                continue
            if size > self.max_file_bytes:
                continue

            content = self.github_client.get_file_content(owner, repository, sha)
            content_bytes = content.encode("utf-8")
            if len(content_bytes) > self.max_file_bytes:
                continue

            chunks = chunk_text_with_locations(
                content, chunk_size=MAX_CHUNK_SIZE, overlap=CHUNK_OVERLAP
            )
            for chunk_index, chunk_info in enumerate(chunks):
                chunk = chunk_info["content"]
                chunk_id = (
                    f"github:{owner}/{repository}@{branch}:{path}::{chunk_index}"
                )
                self.store.add_document(
                    chunk_id=chunk_id,
                    content=chunk,
                    metadata={
                        "document_name": f"{repository}/{path}",
                        "source_type": "github_repository",
                        "document_type": "knowledge",
                        "repository": f"{owner}/{repository}",
                        "branch": branch,
                        "path": path,
                        "blob_sha": sha,
                        "chunk_index": chunk_index,
                        "line_start": chunk_info["line_start"],
                        "line_end": chunk_info["line_end"],
                    },
                )
                chunks_created += 1
            files_indexed += 1

        return {
            "owner": owner,
            "repository": repository,
            "branch": branch,
            "files_seen": files_seen,
            "files_indexed": files_indexed,
            "chunks_created": chunks_created,
        }

    @staticmethod
    def _is_supported_path(path: str) -> bool:
        path_parts = path.replace("\\", "/").split("/")
        if any(part.lower() in EXCLUDED_DIRECTORIES for part in path_parts[:-1]):
            return False
        filename = path_parts[-1]
        if filename.lower() == "dockerfile":
            return True
        dot = filename.rfind(".")
        extension = filename[dot:].lower() if dot >= 0 else ""
        return extension in SUPPORTED_EXTENSIONS
