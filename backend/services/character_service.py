from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any

from services.mongo_service import find_one, find_many

logger = logging.getLogger(__name__)


class CharacterService:
    def get_character_by_key(self, character_key: str) -> Optional[Dict[str, Any]]:
        if not character_key:
            return None

        return find_one(
            "characters",
            {
                "character_key": character_key,
            },
        )

    def get_characters_by_book(self, book_id: str) -> List[Dict[str, Any]]:
        if not book_id:
            return []

        return find_many(
            "characters",
            {
                "book_id": book_id,
            },
            limit=20,
        )

    def get_all_characters(self, limit: int = 50) -> List[Dict[str, Any]]:
        return find_many(
            "characters",
            {},
            limit=limit,
        )


character_service = CharacterService()