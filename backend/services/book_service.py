import logging
from typing import List, Optional
from models.schema import Book
from services.mongo_service import find_many, find_one

logger = logging.getLogger(__name__)


class BookService:
    def get_book_by_id(self, book_id: str) -> Optional[Book]:
        if not book_id:
            return None

        raw_book = find_one("books", {"_id": book_id})

        if not raw_book:
            return None

        try:
            return Book(**raw_book)
        except Exception as e:
            logger.error(f"Error parsing book data for id {book_id}: {e}")
            return None

    def find_books_by_criteria(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        exclude_ids: Optional[List[str]] = None,
        keyword: Optional[str] = None,
        limit: int = 10,
    ) -> List[Book]:
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
                {"summary": {"$regex": keyword, "$options": "i"}},
                {"tags": {"$regex": keyword, "$options": "i"}},
            ]

        raw_books = find_many("books", query, limit=limit)

        books: List[Book] = []

        for raw_book in raw_books:
            try:
                books.append(Book(**raw_book))
            except Exception as e:
                logger.warning(f"Error parsing book document: {e}")

        return books


book_service = BookService()