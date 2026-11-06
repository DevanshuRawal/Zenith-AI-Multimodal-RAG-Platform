from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_compose_defines_api_ui_and_qdrant_services():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]

    assert {"api", "ui", "qdrant", "redis", "worker"}.issubset(services)
    assert services["api"]["build"]["context"] == "."
    assert services["api"]["environment"]["QDRANT_URL"] == "http://qdrant:6333"
    assert services["ui"]["environment"]["BACKEND_URL"] == "http://api:8000"
    assert services["api"]["depends_on"]["qdrant"]["condition"] == "service_healthy"
    assert services["api"]["environment"]["REDIS_URL"] == "redis://redis:6379/0"
    assert services["worker"]["environment"]["QDRANT_URL"] == "http://qdrant:6333"
    assert "celery" in services["worker"]["command"][0]
    assert services["worker"]["depends_on"]["redis"]["condition"] == "service_healthy"
    assert services["worker"]["depends_on"]["qdrant"]["condition"] == "service_healthy"
    assert services["api"]["depends_on"]["redis"]["condition"] == "service_healthy"
    assert services["ui"]["depends_on"]["api"]["condition"] == "service_healthy"
    assert "env_file" not in services["ui"]


def test_api_container_has_runtime_healthcheck_and_persistent_data_mounts():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    api = compose["services"]["api"]

    assert api["healthcheck"]["test"]
    assert any("uploaded_documents" in mount for mount in api["volumes"])
    assert any(mount.endswith(":/data") for mount in api["volumes"])
    assert api["environment"]["SESSION_DB_PATH"] == "/data/sessions.sqlite3"
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "docker-entrypoint" in dockerfile
    assert "chmod 755 /app/docker-entrypoint.sh" in dockerfile
    assert 'CMD ["uvicorn", "app.main:app"' in dockerfile
    assert 'exec "$@"' in (ROOT / "docker-entrypoint.sh").read_text(encoding="utf-8")


def test_docker_build_context_excludes_local_secrets_and_runtime_data():
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()

    assert ".env" in dockerignore
    assert "uploaded_documents/" in dockerignore
    assert "*.sqlite3" in dockerignore


def test_container_deployment_instructions_document_required_secret():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "docker compose up --build" in readme
    assert "HUGGINGFACEHUB_API_TOKEN" in readme


def test_environment_template_documents_requested_rag_defaults():
    settings = dict(
        line.split("=", 1)
        for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    )

    assert settings["MAX_CHUNK_SIZE"] == "1000"
    assert settings["CHUNK_OVERLAP"] == "100"
    assert settings["TOP_K"] == "5"
    assert settings["RETRIEVAL_CANDIDATE_K"] == "20"
    assert settings["SIMILARITY_THRESHOLD"] == "0.7"
