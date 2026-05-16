import unittest
from unittest.mock import patch, call
from backend.services.book_service import BookService

class TestBookService(unittest.TestCase):
    def setUp(self):
        self.service = BookService()

    @patch("services.book_service.find_many")
    @patch("services.book_service.Book")
    def test_find_books_by_criteria_empty(self, mock_book_class, mock_find_many):
        # Arrange: Setup mock return values
        mock_find_many.return_value = [{"_id": "1", "title": "Test Book"}]
        mock_book_class.return_value = "MockedBookInstance"
        
        # Act: Call method with no arguments
        result = self.service.find_books_by_criteria()
        
        # Assert: Verify the empty query was passed and result is correct
        mock_find_many.assert_called_once_with("books", {})
        mock_book_class.assert_called_once_with(_id="1", title="Test Book")
        self.assertEqual(result, ["MockedBookInstance"])

    @patch("services.book_service.find_many")
    @patch("services.book_service.Book")
    def test_find_books_by_criteria_with_all_args(self, mock_book_class, mock_find_many):
        # Arrange
        mock_find_many.return_value = []
        
        # Act: Provide all optional criteria
        result = self.service.find_books_by_criteria(
            category="Fiction",
            tags=["magic", "adventure"],
            exclude_ids=["123", "456"]
        )
        
        # Assert: Check if the MongoDB query was built correctly
        expected_query = {
            "category": "Fiction",
            "tags": {"$in": ["magic", "adventure"]},
            "_id": {"$nin": ["123", "456"]}
        }
        mock_find_many.assert_called_once_with("books", expected_query)
        self.assertEqual(result, [])

    @patch("services.book_service.logger")
    @patch("services.book_service.find_many")
    @patch("services.book_service.Book")
    def test_find_books_by_criteria_parsing_error(self, mock_book_class, mock_find_many, mock_logger):
        # Arrange: Return two raw documents
        mock_find_many.return_value = [{"valid": "data"}, {"invalid": "data"}]
        
        # Make the Book model throw an exception on the second instantiation
        mock_book_class.side_effect = ["GoodBookInstance", Exception("Schema error")]
        
        # Act
        result = self.service.find_books_by_criteria()
        
        # Assert: Ensure it skipped the invalid document but kept the good one
        self.assertEqual(result, ["GoodBookInstance"])
        mock_logger.warning.assert_called_once()

if __name__ == "__main__":
    unittest.main()