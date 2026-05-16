import logging
from typing import List, Optional
from backend.models.schema import Book
from backend.services.mongo_service import find_many, find_one

logger = logging.getLogger(__name__)

class BookService:
    def get_book_by_id(self, book_id: str) -> Optional[Book]:
        raw_book = find_one("books", {"_id": book_id})
        if raw_book:
            try:
                return Book(**raw_book)
            except Exception as e:
                logger.error(f"Error parsing book data for id {book_id}: {e}")
                return None
        return None

    def find_books_by_criteria(self, category: Optional[str] = None, tags: Optional[List[str]] = None, exclude_ids: Optional[List[str]] = None, keyword: Optional[str] = None) -> List[Book]:
        """
        根據分類、標籤、關鍵字查詢書籍，並過濾掉已推薦過的書籍。
        """
        query = {}
        if category:
            query["category"] = category
        if tags:
            query["tags"] = {"$in": tags}
        if exclude_ids:
            query["_id"] = {"$nin": exclude_ids}
        if keyword:
            query["$or"] = [
                {"title": {"$regex": keyword, "$options": "i"}},
                {"summary": {"$regex": keyword, "$options": "i"}}
            ]
            
        raw_books = find_many("books", query)
        
        books = []
        for b in raw_books:
            try:
                books.append(Book(**b))
            except Exception as e:
                logger.warning(f"Error parsing book document: {e}")
                
        return books

book_service = BookService()
