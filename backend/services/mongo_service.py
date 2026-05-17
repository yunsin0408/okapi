from typing import Any, Dict, List, Optional
from backend.core.database import get_db


def find_one(collection: str, query: Dict[str, Any]) -> Optional[Dict]:
    return get_db()[collection].find_one(query)


def find_many(collection: str, query: Dict[str, Any]) -> List[Dict]:
    return list(get_db()[collection].find(query))
