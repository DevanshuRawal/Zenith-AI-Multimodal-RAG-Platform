import pytest


@pytest.fixture(autouse=True)
def default_test_env(monkeypatch):
    monkeypatch.setenv("ENABLE_LOCAL_LLM_FALLBACK", "false")
