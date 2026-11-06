from fastapi.testclient import TestClient

from app import main
from app.github_indexer import GitHubRepositoryIndexer


class FakeGitHubClient:
    def __init__(self):
        self.requested = []

    def get_default_branch(self, owner, repository):
        return "main"

    def list_files(self, owner, repository, branch):
        assert branch == "main"
        return [
            {"path": "README.md", "sha": "readme", "size": 42},
            {"path": "src/api.py", "sha": "api", "size": 36},
            {"path": "assets/diagram.png", "sha": "image", "size": 20},
            {"path": "vendor/generated.py", "sha": "vendor", "size": 9},
            {"path": "src/large.py", "sha": "large", "size": 129},
        ]

    def get_file_content(self, owner, repository, sha):
        self.requested.append(sha)
        return {
            "readme": "# Service architecture\nThe API routes requests.",
            "api": "def route_request():\n    return 'ok'\n",
            "image": "not text",
            "vendor": "generated",
            "large": "large",
        }[sha]


def test_github_client_decodes_blob_and_uses_fixed_github_api():
    import base64

    from app.github_indexer import GitHubClient

    class Response:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "encoding": "base64",
                "content": base64.b64encode(b"print('hello')").decode("ascii"),
            }

    class Session:
        def __init__(self):
            self.headers = {}
            self.requested_url = None

        def get(self, url, params=None, timeout=None):
            self.requested_url = url
            assert timeout == (5, 30)
            return Response()

    session = Session()
    content = GitHubClient(token=None, session=session).get_file_content(
        "owner", "repo", "blob-sha"
    )

    assert content == "print('hello')"
    assert session.requested_url == (
        "https://api.github.com/repos/owner/repo/git/blobs/blob-sha"
    )


class FakeStore:
    def __init__(self):
        self.documents = []

    def add_document(self, chunk_id, content, metadata):
        self.documents.append(
            {"chunk_id": chunk_id, "content": content, "metadata": metadata}
        )


def test_repository_indexer_indexes_supported_repo_files_and_metadata():
    store = FakeStore()
    github = FakeGitHubClient()
    indexer = GitHubRepositoryIndexer(
        store=store,
        github_client=github,
        max_file_bytes=128,
        max_files=10,
    )

    result = indexer.index("example-org", "example-repo")

    assert result == {
        "owner": "example-org",
        "repository": "example-repo",
        "branch": "main",
        "files_seen": 5,
        "files_indexed": 2,
        "chunks_created": 2,
    }
    assert github.requested == ["readme", "api"]
    assert [doc["metadata"]["source_type"] for doc in store.documents] == [
        "github_repository",
        "github_repository",
    ]
    assert store.documents[0]["metadata"]["repository"] == "example-org/example-repo"
    assert store.documents[0]["metadata"]["path"] == "README.md"
    assert store.documents[1]["metadata"]["path"] == "src/api.py"


def test_repository_indexer_enforces_file_size_and_count_limits():
    class LimitedGitHub(FakeGitHubClient):
        def list_files(self, owner, repository, branch):
            return [
                {"path": "one.md", "sha": "one", "size": 20},
                {"path": "two.md", "sha": "two", "size": 20},
                {"path": "three.md", "sha": "three", "size": 20},
            ]

        def get_file_content(self, owner, repository, sha):
            return "x" * 20

    store = FakeStore()
    indexer = GitHubRepositoryIndexer(
        store=store,
        github_client=LimitedGitHub(),
        max_file_bytes=10,
        max_files=2,
    )

    result = indexer.index("owner", "repo")

    assert result["files_seen"] == 2
    assert result["files_indexed"] == 0
    assert result["chunks_created"] == 0
    assert store.documents == []


def test_repository_index_job_api_enqueues_and_returns_job_identifier(monkeypatch):
    class FakeTask:
        def delay(self, owner, repository):
            assert (owner, repository) == ("example-org", "example-repo")
            return type("Job", (), {"id": "job-123"})()

    monkeypatch.setattr(main, "index_github_repository", FakeTask())
    response = TestClient(main.app).post(
        "/api/index/github",
        json={"owner": "example-org", "repository": "example-repo"},
    )

    assert response.status_code == 202
    assert response.json() == {"job_id": "job-123", "status": "queued"}


def test_repository_index_status_api_returns_job_state(monkeypatch):
    class FakeTask:
        def AsyncResult(self, job_id):
            assert job_id == "job-123"
            return type(
                "Result",
                (),
                {
                    "state": "SUCCESS",
                    "result": {"files_indexed": 2, "chunks_created": 7},
                    "info": None,
                    "successful": lambda self: True,
                    "failed": lambda self: False,
                },
            )()

    monkeypatch.setattr(main, "index_github_repository", FakeTask())
    response = TestClient(main.app).get("/api/index/jobs/job-123")

    assert response.status_code == 200
    assert response.json() == {
        "job_id": "job-123",
        "status": "SUCCESS",
        "result": {"files_indexed": 2, "chunks_created": 7},
        "error": None,
    }


def test_repository_index_failed_job_hides_worker_exception(monkeypatch):
    class FakeTask:
        def AsyncResult(self, job_id):
            return type(
                "Result",
                (),
                {
                    "state": "FAILURE",
                    "result": RuntimeError("secret token details"),
                    "successful": lambda self: False,
                    "failed": lambda self: True,
                },
            )()

    monkeypatch.setattr(main, "index_github_repository", FakeTask())
    response = TestClient(main.app).get("/api/index/jobs/job-123")

    assert response.status_code == 200
    assert response.json()["error"] == (
        "Indexing failed. Check worker logs for details."
    )
    assert "secret token" not in response.text


def test_repository_index_endpoint_rejects_invalid_owner_or_repo():
    response = TestClient(main.app).post(
        "/api/index/github",
        json={"owner": "../etc", "repository": "repo"},
    )

    assert response.status_code == 422


def test_celery_task_runs_repository_indexer(monkeypatch):
    import app.worker

    calls = {}

    class Store:
        pass

    class Indexer:
        def __init__(self, store):
            calls["store"] = store

        def index(self, owner, repository):
            calls["repository"] = (owner, repository)
            return {"files_indexed": 1, "chunks_created": 2}

    monkeypatch.setattr(app.worker, "QdrantVectorStore", Store)
    monkeypatch.setattr(app.worker, "GitHubRepositoryIndexer", Indexer)

    result = app.worker.index_github_repository.run("example-org", "example-repo")

    assert result == {"files_indexed": 1, "chunks_created": 2}
    assert calls["repository"] == ("example-org", "example-repo")
    assert isinstance(calls["store"], Store)
