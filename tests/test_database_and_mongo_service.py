import unittest
import mongomock
from unittest.mock import patch


SAMPLE_BOOK = {
    "_id": "book1",
    "title": "測試書",
    "author": "作者A",
    "category": "小說",
    "summary": "測試摘要",
    "tags": ["愛情", "青春"],
    "purchase_url": "http://example.com/buy",
    "sample_link": "http://example.com/sample",
}


def make_mock_db():
    client = mongomock.MongoClient()
    db = client["okapi"]
    db["books"].insert_one(SAMPLE_BOOK.copy())
    return db


class TestMongoService(unittest.TestCase):
    def setUp(self):
        self.mock_db = make_mock_db()
        self.patcher = patch("backend.core.database.get_db", return_value=self.mock_db)
        self.patcher.start()
        # 強制重新 import，讓 patch 生效
        import importlib
        import backend.services.mongo_service as ms
        importlib.reload(ms)
        self.mongo_service = ms

    def tearDown(self):
        self.patcher.stop()

    def test_find_one_existing(self):
        result = self.mongo_service.find_one("books", {"_id": "book1"})
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "測試書")

    def test_find_one_not_found(self):
        result = self.mongo_service.find_one("books", {"_id": "notexist"})
        self.assertIsNone(result)

    def test_find_many_match(self):
        results = self.mongo_service.find_many("books", {"category": "小說"})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["author"], "作者A")

    def test_find_many_no_match(self):
        results = self.mongo_service.find_many("books", {"category": "科幻"})
        self.assertEqual(results, [])

    def test_find_many_returns_list(self):
        results = self.mongo_service.find_many("books", {})
        self.assertIsInstance(results, list)

    def test_find_many_tag_filter(self):
        results = self.mongo_service.find_many("books", {"tags": {"$in": ["愛情"]}})
        self.assertEqual(len(results), 1)

    def test_insert_one_returns_id(self):
        new_book = {
            "_id": "book2",
            "title": "新書",
            "author": "作者B",
            "category": "科幻",
            "summary": "摘要",
            "tags": [],
            "purchase_url": "",
            "sample_link": "",
        }
        inserted_id = self.mongo_service.insert_one("books", new_book)
        self.assertEqual(inserted_id, "book2")
        result = self.mongo_service.find_one("books", {"_id": "book2"})
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "新書")

    def test_update_one_modifies_field(self):
        modified = self.mongo_service.update_one("books", {"_id": "book1"}, {"title": "更新後的書名"})
        self.assertEqual(modified, 1)
        result = self.mongo_service.find_one("books", {"_id": "book1"})
        self.assertEqual(result["title"], "更新後的書名")

    def test_update_one_no_match(self):
        modified = self.mongo_service.update_one("books", {"_id": "notexist"}, {"title": "X"})
        self.assertEqual(modified, 0)


class TestDatabaseSingleton(unittest.TestCase):
    def test_get_db_returns_same_instance(self):
        """同一程序內兩次呼叫 get_db() 應回傳同一個 db 物件"""
        import backend.core.database as db_module
        original_client = db_module._client
        try:
            mock_client = mongomock.MongoClient()
            db_module._client = None
            with patch("backend.core.database.MongoClient", return_value=mock_client):
                db1 = db_module.get_db()
                db2 = db_module.get_db()
                self.assertIs(db1, db2)
        finally:
            db_module._client = original_client


if __name__ == "__main__":
    unittest.main()
