from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any

from services.mongo_service import find_one, find_many

logger = logging.getLogger(__name__)


class StoryService:
    def get_start_scene(self, book_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        query: Dict[str, Any] = {
            "scene_type": "start",
        }

        if book_id:
            query["book_id"] = book_id

        scene = find_one("story_scenes", query)

        if scene:
            return scene

        fallback_query: Dict[str, Any] = {}

        if book_id:
            fallback_query["book_id"] = book_id

        scenes = find_many("story_scenes", fallback_query, limit=1)

        return scenes[0] if scenes else None

    def get_scene(self, scene_id: str) -> Optional[Dict[str, Any]]:
        if not scene_id:
            return None

        return find_one(
            "story_scenes",
            {
                "_id": scene_id,
            },
        )

    def get_choices_by_scene(self, scene_id: str) -> List[Dict[str, Any]]:
        if not scene_id:
            return []

        return find_many(
            "story_choices",
            {
                "scene_id": scene_id,
            },
            limit=10,
        )

    def choose_option(
        self,
        scene_id: str,
        option_id: str,
    ) -> Dict[str, Any]:
        if not scene_id or not option_id:
            return {
                "ok": False,
                "error_code": "MISSING_SCENE_OR_OPTION",
                "message": "缺少 scene_id 或 option_id。",
            }

        choice = find_one(
            "story_choices",
            {
                "scene_id": scene_id,
                "option_id": option_id,
            },
        )

        if not choice:
            return {
                "ok": False,
                "error_code": "CHOICE_NOT_FOUND",
                "message": "找不到這個故事選項。",
            }

        next_scene_id = choice.get("next_scene_id")
        next_scene = self.get_scene(next_scene_id) if next_scene_id else None
        next_choices = self.get_choices_by_scene(next_scene_id) if next_scene_id else []

        return {
            "ok": True,
            "choice": choice,
            "next_scene": next_scene,
            "next_choices": next_choices,
        }

    def format_scene_response(
        self,
        scene: Dict[str, Any],
        choices: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        choices = choices or []

        formatted_choices = [
            {
                "id": choice.get("option_id") or choice.get("_id"),
                "text": choice.get("text"),
            }
            for choice in choices
        ]

        title = scene.get("title", "故事場景")
        description = scene.get("description", "")

        return {
            "type": "story",
            "text": f"{title}\n{description}",
            "scene_id": scene.get("_id"),
            "book_id": scene.get("book_id"),
            "scene_title": title,
            "description": description,
            "interaction_hint": scene.get("interaction_hint"),
            "options": formatted_choices,
            "action_type": "SHOW_STORY",
        }


story_service = StoryService()