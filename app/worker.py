from celery import Celery

from app.config import REDIS_URL
from app.github_indexer import GitHubRepositoryIndexer
from app.qdrant_store import QdrantVectorStore

celery_app = Celery(
    "zenith",
    broker=REDIS_URL,
    backend=REDIS_URL,
)
celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
)


@celery_app.task(name="zenith.index_github_repository")
def index_github_repository(owner: str, repository: str):
    store = QdrantVectorStore()
    indexer = GitHubRepositoryIndexer(store=store)
    return indexer.index(owner, repository)
