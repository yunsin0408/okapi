from pymongo import MongoClient
from pymongo.database import Database
from backend.core.config import settings

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGO_URI)
    return _client


def get_db() -> Database:
    return get_client()[settings.MONGO_DB_NAME]
