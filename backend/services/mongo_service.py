from typing import Any, Dict, List, Optional
from core.database import get_db


def find_one(collection: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return get_db()[collection].find_one(query)


def find_many(
    collection: str,
    query: Dict[str, Any],
    limit: int = 20,
) -> List[Dict[str, Any]]:
    return list(get_db()[collection].find(query).limit(limit))


def insert_one(collection: str, document: Dict[str, Any]) -> str:
    result = get_db()[collection].insert_one(document)
    return str(result.inserted_id)


def update_one(collection: str, query: Dict[str, Any], update: Dict[str, Any]) -> int:
    result = get_db()[collection].update_one(query, {"$set": update}, upsert=True)
    return result.modified_count