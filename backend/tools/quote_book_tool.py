import logging
from typing import Any, Dict, List, Optional

from models.schema import MoodIntentOutput, QuoteBookOutput
from services.book_service import book_service
from services.quote_service import quote_service

logger = logging.getLogger(__name__)


class QuoteBookTool:
    def recommend(
        self,
        user_state: Any,
        exclude_book_ids: Optional[List[str]] = None,
        exclude_quote_ids: Optional[List[str]] = None,
    ) -> QuoteBookOutput:
        exclude_book_ids = exclude_book_ids or []
        exclude_quote_ids = exclude_quote_ids or []

        state = self._normalize_user_state(user_state)

        mood = state.mood
        scene = state.scene
        keyword = None

        tags = []
        if mood and mood != "neutral":
            tags.append(mood)

        books = book_service.find_books_by_criteria(
            tags=tags,
            exclude_ids=exclude_book_ids,
            limit=10,
        )

        if not books:
            books = book_service.find_books_by_criteria(
                keyword=keyword,
                exclude_ids=exclude_book_ids,
                limit=10,
            )

        if not books:
            books = book_service.find_books_by_criteria(
                exclude_ids=exclude_book_ids,
                limit=10,
            )

        if not books:
            return QuoteBookOutput(
                book=None,
                quote=None,
                reason="目前資料庫查不到符合條件的書籍，請先確認 books collection 是否已有資料。",
                confidence_score=0.0,
            )

        selected_book = books[0]

        quotes = quote_service.get_quotes_by_emotion(
            emotion=mood,
            scene=scene,
            book_id=selected_book.id,
            exclude_quote_ids=exclude_quote_ids,
            exclude_book_ids=exclude_book_ids,
        )

        selected_quote = quotes[0] if quotes else None

        reason = self._build_reason(mood=mood, book_title=selected_book.title)

        return QuoteBookOutput(
            book=selected_book,
            quote=selected_quote,
            reason=reason,
            confidence_score=0.82 if selected_quote else 0.65,
        )

    def _normalize_user_state(self, user_state: Any) -> MoodIntentOutput:
        if isinstance(user_state, MoodIntentOutput):
            return user_state

        if hasattr(user_state, "model_dump"):
            data = user_state.model_dump()
        elif hasattr(user_state, "dict"):
            data = user_state.dict()
        elif isinstance(user_state, dict):
            data = user_state
        else:
            data = {}

        return MoodIntentOutput(
            mood=data.get("mood", "neutral"),
            intent=data.get("intent", "recommendation"),
            scene=data.get("scene", "general"),
            tone=data.get("tone", "neutral"),
            should_trigger_tool=data.get("should_trigger_tool", True),
        )

    def _build_reason(self, mood: str, book_title: str) -> str:
        if mood and mood != "neutral":
            return f"因為你現在的狀態比較接近「{mood}」，所以我推薦《{book_title}》，它比較適合拿來陪你整理情緒。"

        return f"我推薦《{book_title}》，這本書適合現在想找一本書開始閱讀的人。"


quote_book_tool = QuoteBookTool()