from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List, Callable

logger = logging.getLogger(__name__)


class BookAgent:
    """
    BookAgent 是整個後端聊天流程的總控台。

    最終版原則：
    1. 不使用 mock 資料。
    2. 工具失敗就回傳正式錯誤。
    3. 所有輸出都統一成前端可接的 response schema。
    4. Agent 只負責 orchestration，不把工具邏輯塞在這裡。
    """

    def __init__(self):
        self.mood_intent_tool = self._safe_import_tool(
            "mood_intent",
            self._import_mood_intent_tool,
        )
        self.quote_book_tool = self._safe_import_tool(
            "quote_book",
            self._import_quote_book_tool,
        )
        self.quiz_story_tool = self._safe_import_tool(
            "quiz_story",
            self._import_quiz_story_tool,
        )
        self.preview_purchase_tool = self._safe_import_tool(
            "preview_purchase",
            self._import_preview_purchase_tool,
        )
        self.story_tool = self._safe_import_tool(
            "story",
            self._import_story_tool,
        )

        logger.info("BookAgent initialized")

    # ------------------------------------------------------------------
    # Tool import
    # ------------------------------------------------------------------

    def _safe_import_tool(self, tool_name: str, import_func: Callable[[], Any]) -> Any:
        try:
            return import_func()
        except Exception as exc:
            logger.error("Tool import failed: %s, error=%s", tool_name, exc)
            return None

    def _import_mood_intent_tool(self):
        from tools.mood_intent_tool import mood_intent_tool
        return mood_intent_tool

    def _import_quote_book_tool(self):
        from tools.quote_book_tool import quote_book_tool
        return quote_book_tool

    def _import_quiz_story_tool(self):
        from tools.quiz_story_tool import quiz_story_tool
        return quiz_story_tool

    def _import_preview_purchase_tool(self):
        from tools.preview_purchase_tool import preview_purchase_tool
        return preview_purchase_tool
    
    def _import_story_tool(self):
        from tools.story_tool import story_tool
        return story_tool

    # ------------------------------------------------------------------
    # Main flow
    # ------------------------------------------------------------------

    def run(
        self,
        user_id: str,
        user_input: str,
        interaction_id: Optional[str] = None,
        current_book_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        validation = self.validate_user_input(user_input)

        if not validation["is_valid"]:
            return self.build_response(
                text=validation["message"],
                action_type="CHAT",
                route="input_error",
                mood_intent=self.default_mood_intent(),
                result={
                    "error_code": validation["error_code"],
                },
                suggestions=["推薦一本書給我", "我想做測驗"],
            )

        mood_intent = self.analyze_mood_and_intent(user_input)
        route = self.decide_route(
            mood_intent=mood_intent,
            interaction_id=interaction_id,
        )

        route_handler_map = {
            "quote_book": self.handle_quote_book,
            "quiz_story": self.handle_quiz_story,
            "preview_purchase": self.handle_preview_purchase,
            "continue_interaction": self.handle_continue_interaction,
            "greeting": self.handle_greeting,
            "general_chat": self.handle_general_chat,
        }

        handler = route_handler_map.get(route, self.handle_general_chat)

        try:
            result = handler(
                user_id=user_id,
                user_input=user_input,
                mood_intent=mood_intent,
                interaction_id=interaction_id,
                current_book_id=current_book_id,
            )
            return result
        except Exception as exc:
            logger.exception("BookAgent route failed. route=%s error=%s", route, exc)
            return self.build_response(
                text="系統處理時發生錯誤，請稍後再試。",
                action_type="CHAT",
                route=route,
                mood_intent=mood_intent,
                result={
                    "error_code": "AGENT_ROUTE_FAILED",
                    "detail": str(exc),
                },
                suggestions=["重新推薦一本書", "回到首頁"],
            )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_user_input(self, user_input: str) -> Dict[str, Any]:
        if user_input is None:
            return {
                "is_valid": False,
                "error_code": "EMPTY_INPUT",
                "message": "我沒有收到你的訊息，可以再輸入一次嗎？",
            }

        cleaned = user_input.strip()

        if not cleaned:
            return {
                "is_valid": False,
                "error_code": "EMPTY_INPUT",
                "message": "你剛剛好像沒有輸入內容，可以告訴我你想找什麼書嗎？",
            }

        if len(cleaned) > 500:
            return {
                "is_valid": False,
                "error_code": "INPUT_TOO_LONG",
                "message": "你的訊息有點太長了，可以先用一兩句話告訴我你想找哪類書嗎？",
            }

        meaningful_chars = [
            ch for ch in cleaned
            if ch.isalnum() or "\u4e00" <= ch <= "\u9fff"
        ]

        if len(meaningful_chars) == 0:
            return {
                "is_valid": False,
                "error_code": "NO_MEANINGFUL_TEXT",
                "message": "我看不太懂這段內容，可以用文字描述你想找的書或心情嗎？",
            }

        return {
            "is_valid": True,
            "error_code": None,
            "message": "ok",
        }

    # ------------------------------------------------------------------
    # Mood / intent
    # ------------------------------------------------------------------

    def default_mood_intent(self) -> Dict[str, Any]:
        return {
            "mood": "neutral",
            "intent": "general_chat",
            "scene": "general",
            "tone": "neutral",
            "should_trigger_tool": False,
            "source": "default",
        }

    def analyze_mood_and_intent(self, user_input: str) -> Dict[str, Any]:
        if self.mood_intent_tool is not None:
            try:
                result = self.mood_intent_tool.analyze(user_input)
                return self.normalize_mood_intent(result, source="tool")
            except Exception as exc:
                logger.error("Mood intent tool failed: %s", exc)

        return self.rule_based_mood_intent(user_input)

    def normalize_mood_intent(self, result: Any, source: str) -> Dict[str, Any]:
        if hasattr(result, "model_dump"):
            data = result.model_dump()
        elif hasattr(result, "dict"):
            data = result.dict()
        elif isinstance(result, dict):
            data = result
        else:
            data = {}

        return {
            "mood": data.get("mood", "neutral"),
            "intent": data.get("intent", "general_chat"),
            "scene": data.get("scene", "general"),
            "tone": data.get("tone", "neutral"),
            "should_trigger_tool": data.get(
                "should_trigger_tool",
                data.get("should_trigger_recommendation", False),
            ),
            "source": source,
        }

    def rule_based_mood_intent(self, user_input: str) -> Dict[str, Any]:
        text = user_input.lower().strip()

        if any(word in text for word in ["購買", "試讀", "連結", "哪裡買", "價格", "買"]):
            return {
                "mood": "neutral",
                "intent": "preview_purchase",
                "scene": "purchase",
                "tone": "direct",
                "should_trigger_tool": True,
                "source": "rule_based",
            }
        
        if any(word in text for word in ["故事", "劇情", "互動", "冒險", "沉浸"]):
            return {
                "mood": "curious",
                "intent": "story",
                "scene": "story",
                "tone": "curious",
                "should_trigger_tool": True,
                "source": "rule_based",
            }

        if any(word in text for word in ["測驗", "人格", "角色", "我是誰", "適合哪本"]):
            return {
                "mood": "curious",
                "intent": "quiz",
                "scene": "quiz",
                "tone": "curious",
                "should_trigger_tool": True,
                "source": "rule_based",
            }

        if any(word in text for word in ["累", "壓力", "難過", "焦慮", "煩", "低落", "迷茫", "推薦", "想看", "書", "找一本"]):
            return {
                "mood": "低落",
                "intent": "recommendation",
                "scene": "recommendation",
                "tone": "supportive",
                "should_trigger_tool": True,
                "source": "rule_based",
            }

        if any(word in text for word in ["嗨", "哈囉", "你好", "hello", "hi"]):
            return {
                "mood": "neutral",
                "intent": "greeting",
                "scene": "general",
                "tone": "casual",
                "should_trigger_tool": False,
                "source": "rule_based",
            }

        return self.default_mood_intent() | {
            "source": "rule_based",
        }

    # ------------------------------------------------------------------
    # Route decision
    # ------------------------------------------------------------------

    def decide_route(
        self,
        mood_intent: Dict[str, Any],
        interaction_id: Optional[str] = None,
    ) -> str:
        if interaction_id:
            return "continue_interaction"

        intent = mood_intent.get("intent", "general_chat")

        if intent in ["recommendation", "comfort"]:
            return "quote_book"

        if intent == "quiz":
            return "quiz_story"

        if intent == "preview_purchase":
            return "preview_purchase"

        if intent == "greeting":
            return "greeting"

        return "general_chat"

    # ------------------------------------------------------------------
    # Route handlers
    # ------------------------------------------------------------------

    def handle_quote_book(
        self,
        user_id: str,
        user_input: str,
        mood_intent: Dict[str, Any],
        interaction_id: Optional[str],
        current_book_id: Optional[str],
    ) -> Dict[str, Any]:
        if self.quote_book_tool is None:
            return self.build_response(
                text="推薦工具目前尚未完成或無法載入。",
                action_type="CHAT",
                route="quote_book",
                mood_intent=mood_intent,
                result={
                    "error_code": "QUOTE_BOOK_TOOL_UNAVAILABLE",
                },
                suggestions=["稍後再試", "回到首頁"],
            )

        result = self.quote_book_tool.recommend(mood_intent)
        data = self.normalize_tool_result(result)

        book = data.get("book")
        quote = data.get("quote")

        if not book:
            return self.build_response(
                text=data.get("reason", "目前查不到符合條件的書籍。"),
                action_type="CHAT",
                route="quote_book",
                mood_intent=mood_intent,
                result={
                    "error_code": "NO_BOOK_FOUND",
                    "raw_result": data,
                },
                suggestions=["換一種心情描述", "重新推薦一本書"],
            )

        book_title = book.get("title", "這本書")
        reason = data.get("reason", "")

        text_parts = [f"我推薦你看《{book_title}》。"]

        if reason:
            text_parts.append(reason)

        if quote and quote.get("content"):
            text_parts.append(f"也送你一句書中的話：{quote.get('content')}")

        return self.build_response(
            text="\n".join(text_parts),
            action_type="SHOW_BOOK",
            route="quote_book",
            mood_intent=mood_intent,
            result=data,
            suggestions=["查看試讀", "哪裡買", "換一本書", "開始測驗"],
        )

    def handle_quiz_story(
        self,
        user_id: str,
        user_input: str,
        mood_intent: Dict[str, Any],
        interaction_id: Optional[str],
        current_book_id: Optional[str],
    ) -> Dict[str, Any]:
        if self.quiz_story_tool is None:
            return self.build_response(
                text="測驗工具目前尚未完成或無法載入。",
                action_type="CHAT",
                route="quiz_story",
                mood_intent=mood_intent,
                result={
                    "error_code": "QUIZ_STORY_TOOL_UNAVAILABLE",
                },
                suggestions=["直接推薦一本書", "回到首頁"],
            )

        if hasattr(self.quiz_story_tool, "start_quiz"):
            result = self.quiz_story_tool.start_quiz(user_id=user_id)
        elif hasattr(self.quiz_story_tool, "run"):
            result = self.quiz_story_tool.run(
                user_id=user_id,
                user_input=user_input,
                interaction_id=interaction_id,
            )
        else:
            return self.build_response(
                text="測驗工具缺少 start_quiz 或 run 方法。",
                action_type="CHAT",
                route="quiz_story",
                mood_intent=mood_intent,
                result={
                    "error_code": "QUIZ_METHOD_NOT_FOUND",
                },
                suggestions=["直接推薦一本書"],
            )

        data = self.normalize_tool_result(result)

        return self.build_response(
            text=data.get("text", "我們開始一個小測驗吧。"),
            action_type="SHOW_QUIZ",
            route="quiz_story",
            mood_intent=mood_intent,
            result=data,
            suggestions=["直接推薦一本書", "重新開始測驗"],
        )

    def handle_preview_purchase(
        self,
        user_id: str,
        user_input: str,
        mood_intent: Dict[str, Any],
        interaction_id: Optional[str],
        current_book_id: Optional[str],
    ) -> Dict[str, Any]:
        if self.preview_purchase_tool is None:
            return self.build_response(
                text="試讀與購買工具目前尚未完成或無法載入。",
                action_type="CHAT",
                route="preview_purchase",
                mood_intent=mood_intent,
                result={
                    "error_code": "PREVIEW_PURCHASE_TOOL_UNAVAILABLE",
                },
                suggestions=["先推薦一本書", "回到首頁"],
            )

        result = self.preview_purchase_tool.run(
            user_id=user_id,
            current_book_id=current_book_id,
        )

        data = self.normalize_tool_result(result)

        if data.get("error_code"):
            return self.build_response(
                text=data.get("text", "目前無法取得試讀與購買資訊。"),
                action_type="CHAT",
                route="preview_purchase",
                mood_intent=mood_intent,
                result=data,
                suggestions=["先推薦一本書", "換一本書"],
            )

        return self.build_response(
            text=data.get("text", "這裡是試讀與購買資訊。"),
            action_type="SHOW_PURCHASE",
            route="preview_purchase",
            mood_intent=mood_intent,
            result=data,
            suggestions=["查看試讀", "前往購買", "換一本書"],
        )

    def handle_continue_interaction(
        self,
        user_id: str,
        user_input: str,
        mood_intent: Dict[str, Any],
        interaction_id: Optional[str],
        current_book_id: Optional[str],
    ) -> Dict[str, Any]:
        if self.quiz_story_tool is not None and hasattr(self.quiz_story_tool, "answer_quiz"):
            result = self.quiz_story_tool.answer_quiz(
                user_id=user_id,
                interaction_id=interaction_id,
                user_input=user_input,
            )
            data = self.normalize_tool_result(result)

            return self.build_response(
                text=data.get("text", "我收到你的選擇了。"),
                action_type=data.get("action_type", "SHOW_QUIZ"),
                route="continue_interaction",
                mood_intent=mood_intent,
                result=data,
                suggestions=["繼續", "重新開始測驗"],
            )

        return self.build_response(
            text="目前無法續接這個互動流程，請重新開始測驗。",
            action_type="CHAT",
            route="continue_interaction",
            mood_intent=mood_intent,
            result={
                "error_code": "INTERACTION_CONTINUE_UNAVAILABLE",
                "interaction_id": interaction_id,
            },
            suggestions=["重新開始測驗", "直接推薦一本書"],
        )

    def handle_greeting(
        self,
        user_id: str,
        user_input: str,
        mood_intent: Dict[str, Any],
        interaction_id: Optional[str],
        current_book_id: Optional[str],
    ) -> Dict[str, Any]:
        return self.build_response(
            text="嗨！你可以告訴我最近的心情，或直接說想找哪一類的書，我會幫你推薦。",
            action_type="CHAT",
            route="greeting",
            mood_intent=mood_intent,
            result={},
            suggestions=["我最近壓力很大", "推薦一本書給我", "我想做測驗"],
        )

    def handle_general_chat(
        self,
        user_id: str,
        user_input: str,
        mood_intent: Dict[str, Any],
        interaction_id: Optional[str],
        current_book_id: Optional[str],
    ) -> Dict[str, Any]:
        return self.build_response(
            text="我目前可以幫你做書籍推薦、金句推薦、閱讀測驗，或提供試讀與購買連結。你可以說：我最近很累，推薦一本書給我。",
            action_type="CHAT",
            route="general_chat",
            mood_intent=mood_intent,
            result={},
            suggestions=["推薦一本書給我", "我想做測驗", "查看試讀"],
        )

    # ------------------------------------------------------------------
    # Normalize / response
    # ------------------------------------------------------------------

    def normalize_tool_result(self, result: Any) -> Dict[str, Any]:
        if result is None:
            return {}

        if hasattr(result, "model_dump"):
            return result.model_dump(by_alias=False)

        if hasattr(result, "dict"):
            return result.dict()

        if isinstance(result, dict):
            return result

        return {
            "raw_result": str(result),
        }

    def build_response(
        self,
        text: str,
        action_type: str,
        route: str,
        mood_intent: Dict[str, Any],
        result: Dict[str, Any],
        suggestions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return {
            "text_content": text,
            "action_type": action_type,
            "data_payload": {
                "route": route,
                "mood_intent": mood_intent,
                "result": result,
            },
            "suggestions": suggestions or [],
        }