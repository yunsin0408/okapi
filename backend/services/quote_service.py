import random
from typing import List
from models.schema import Quote
from services.mongo_service import find_many

class QuoteService:
    def get_quotes_by_emotion(self, emotion: str, scene: str = None, exclude_book_ids: List[str] = None) -> List[Quote]:
        query = {}
        
        # 透過 emotion_tags 進行配對
        if emotion:
            query["emotion_tags"] = {"$in": [emotion]}
            
        raw_quotes = find_many("quotes", query)
        
        if not raw_quotes and scene:
            # 如果用 emotion 找不到，嘗試找全部再退化過濾，或根據場景
            raw_quotes = find_many("quotes", {})
            
        quotes = []
        for q in raw_quotes:
            try:
                quotes.append(Quote(**q))
            except Exception:
                pass
                
        # 過濾已推薦過的書的金句
        if exclude_book_ids:
            quotes = [q for q in quotes if q.book_ref not in exclude_book_ids]
            
        random.shuffle(quotes)
        return quotes

quote_service = QuoteService()
