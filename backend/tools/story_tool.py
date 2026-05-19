from __future__ import annotations

from typing import Dict, Any, Optional

from services.story_service import story_service
from services.mongo_service import find_one, update_one


class StoryTool:
    def start_story(
        self,
        user_id: str,
        current_book_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        scene = story_service.get_start_scene(book_id=current_book_id)

        if not scene:
            return {
                "type": "story",
                "text": "目前資料庫沒有互動故事場景，請先建立 story_scenes 資料。",
                "error_code": "NO_STORY_SCENE",
                "options": [],
                "action_type": "CHAT",
            }

        choices = story_service.get_choices_by_scene(scene.get("_id"))

        self._save_story_state(
            user_id=user_id,
            state={
                "user_id": user_id,
                "current_scene_id": scene.get("_id"),
                "current_book_id": current_book_id or scene.get("book_id"),
                "status": "in_progress",
            },
        )

        return story_service.format_scene_response(scene, choices)

    def answer_story(
        self,
        user_id: str,
        user_input: str,
    ) -> Dict[str, Any]:
        state = self._get_story_state(user_id)

        if not state:
            return {
                "type": "story",
                "text": "目前沒有進行中的互動故事，請重新開始故事。",
                "error_code": "NO_ACTIVE_STORY",
                "action_type": "CHAT",
            }

        scene_id = state.get("current_scene_id")
        option_id = user_input.strip().upper()

        result = story_service.choose_option(
            scene_id=scene_id,
            option_id=option_id,
        )

        if not result.get("ok"):
            return {
                "type": "story",
                "text": result.get("message", "找不到這個故事選項。"),
                "error_code": result.get("error_code", "STORY_CHOICE_ERROR"),
                "action_type": "SHOW_STORY",
            }

        choice = result.get("choice", {})
        next_scene = result.get("next_scene")
        next_choices = result.get("next_choices", [])

        if not next_scene:
            self._save_story_state(
                user_id=user_id,
                state={
                    **state,
                    "status": "completed",
                },
            )

            return {
                "type": "story",
                "text": choice.get("static_reply", "故事到這裡告一段落。"),
                "choice": choice,
                "action_type": "CHAT",
            }

        self._save_story_state(
            user_id=user_id,
            state={
                **state,
                "current_scene_id": next_scene.get("_id"),
            },
        )

        response = story_service.format_scene_response(next_scene, next_choices)

        if choice.get("static_reply"):
            response["text"] = f"{choice.get('static_reply')}\n\n{response['text']}"

        return response

    def _get_story_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        return find_one(
            "story_states",
            {
                "user_id": user_id,
            },
        )

    def _save_story_state(
        self,
        user_id: str,
        state: Dict[str, Any],
    ) -> None:
        update_one(
            "story_states",
            {
                "user_id": user_id,
            },
            state,
        )


story_tool = StoryTool()
