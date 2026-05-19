import random
import logging
from typing import List, Optional
from models.schema import Quote
from services.mongo_service import find_many

logger = logging.getLogger(__name__)


class QuoteService:
    def get_quotes_by_emotion(
        self,
        emotion: Optional[str] = None,
        scene: Optional[str] = None,
        book_id: Optional[str] = None,
        exclude_quote_ids: Optional[List[str]] = None,
        exclude_book_ids: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Quote]:
        query = {}

        if book_id:
            query["book_ref"] = book_id

        if emotion and emotion != "neutral":
            query["emotion_tags"] = {"$in": [emotion]}

        if exclude_quote_ids:
            query["_id"] = {"$nin": exclude_quote_ids}

        raw_quotes = find_many("quotes", query, limit=limit)

        if not raw_quotes and book_id:
            fallback_query = {"book_ref": book_id}

            if exclude_quote_ids:
                fallback_query["_id"] = {"$nin": exclude_quote_ids}

            raw_quotes = find_many("quotes", fallback_query, limit=limit)

        if not raw_quotes and emotion and emotion != "neutral":
            fallback_query = {"emotion_tags": {"$in": [emotion]}}

            if exclude_quote_ids:
                fallback_query["_id"] = {"$nin": exclude_quote_ids}

            raw_quotes = find_many("quotes", fallback_query, limit=limit)

        if not raw_quotes:
            fallback_query = {}

            if exclude_quote_ids:
                fallback_query["_id"] = {"$nin": exclude_quote_ids}

            raw_quotes = find_many("quotes", fallback_query, limit=limit)

        quotes: List[Quote] = []

        for raw_quote in raw_quotes:
            try:
                quote = Quote(**raw_quote)

                if exclude_book_ids and quote.book_ref in exclude_book_ids:
                    continue

                quotes.append(quote)
            except Exception as e:
                logger.warning(f"Error parsing quote document: {e}")

        random.shuffle(quotes)
        return quotes


quote_service = QuoteService()