from typing import Any, Dict, List, Optional
from backend.core.database import get_db


def find_one(collection: str, query: Dict[str, Any]) -> Optional[Dict]:
    return get_db()[collection].find_one(query)


def find_many(collection: str, query: Dict[str, Any]) -> List[Dict]:
    return list(get_db()[collection].find(query))


def insert_one(collection: str, document: Dict[str, Any]) -> str:
    result = get_db()[collection].insert_one(document)
    return str(result.inserted_id)


def update_one(collection: str, query: Dict[str, Any], update: Dict[str, Any]) -> int:
    result = get_db()[collection].update_one(query, {"$set": update})
    return result.modified_count
