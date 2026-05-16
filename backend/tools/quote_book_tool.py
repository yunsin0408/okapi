import logging
from typing import List, Optional
from backend.services.book_service import book_service
from backend.services.quote_service import quote_service
from backend.models.schema import MoodIntentOutput, QuoteBookOutput, BookCard, QuoteCard

logger = logging.getLogger(__name__)

class QuoteBookTool:
    """
    推薦整合器：根據使用者狀態與過往歷史，找出最適合的書籍與金句組合，
    並產生標準化推薦卡片格式。
    """
    
    def recommend(
        self, 
        user_state: MoodIntentOutput, 
        exclude_book_ids: Optional[List[str]] = None,
        exclude_quote_ids: Optional[List[str]] = None
    ) -> QuoteBookOutput:
        exclude_book_ids = exclude_book_ids or []
        exclude_quote_ids = exclude_quote_ids or []
        
        logger.info(f"Running recommendation logic for state: {user_state.mood}")
        
        # 1. 根據使用者的情緒與意圖去查找書籍 (語意匹配)
        tags = [user_state.mood] if user_state.mood and user_state.mood != "neutral" else []
        books = book_service.find_books_by_criteria(tags=tags, exclude_ids=exclude_book_ids)
        
        # Fallback 機制：如果找不到書籍，則放寬條件搜尋 (拿掉標籤限制)
        if not books:
            logger.warning("No books found matching criteria, executing fallback strategy.")
            books = book_service.find_books_by_criteria(exclude_ids=exclude_book_ids)
        
        # 2. 取得一本書與其相關金句
        book_card = None
        quote_card = None
        
        if books:
            selected_book = books[0] # 取出最推薦的第一本書
            book_card = BookCard(book=selected_book)
            
            # 試著找出這本書對應的金句；若無，則根據情境尋找其他替代金句
            quotes = quote_service.get_quotes_by_emotion(
                book_id=selected_book.id if hasattr(selected_book, 'id') else None,
                scene=user_state.scene,
                exclude_quote_ids=exclude_quote_ids
            )
            if quotes:
                quote_card = QuoteCard(quote=quotes[0])
                
        return QuoteBookOutput(book_card=book_card, quote_card=quote_card)

quote_book_tool = QuoteBookTool()