"""One-off script: import quotes from wide-layout CSV into MongoDB ``quotes``."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()


def import_quotes(csv_path: str) -> None:
    """Parse wide-layout ``quotes.csv`` and insert into ``quotes`` after resolving ``book_ref``.

    CSV layout matches ``books.csv``: first column holds field names
    (``book_title``, ``content``, ``emotion_tags``); each column to the right is
    one quote row.

    Args:
        csv_path: Path to ``quotes.csv``.
    """
    mongo_uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_BOOK_DATA", "okapi")
    if not mongo_uri:
        print("錯誤：找不到 MONGO_URI，請檢查 .env 檔案")
        return

    client: MongoClient[Any] = MongoClient(mongo_uri)
    try:
        db = client[db_name]
        books_col = db["books"]
        quotes_col = db["quotes"]

        # Wide sheet: row labels in column 0, one column per quote (same as import_books)
        df = pd.read_csv(csv_path, header=None)
        df = df.set_index(0).T

        quotes_to_insert: list[dict[str, Any]] = []

        print("--- 開始關聯書籍 ID 並解析金句 ---")

        for _, row in df.iterrows():
            book_title_value = str(row["book_title"]).strip()
            if not book_title_value or book_title_value == "book_title":
                continue

            target_book = books_col.find_one({"title": book_title_value})
            if target_book:
                quote_data = {
                    "book_ref": target_book["_id"],
                    "book_title": target_book["title"],
                    "content": str(row["content"]).strip() if pd.notna(row["content"]) else "",
                    "emotion_tags": [
                        tag.strip()
                        for tag in str(row["emotion_tags"]).split(",")
                        if tag.strip()
                    ]
                    if pd.notna(row["emotion_tags"])
                    else [],
                }
                quotes_to_insert.append(quote_data)
                print(f"成功關聯: {book_title_value}（金句已排入佇列）")
            else:
                print(f"警告：找不到書名為 '{book_title_value}' 的書籍，請檢查 CSV 或先匯入 books")

        if quotes_to_insert:
            quotes_col.delete_many({})
            quotes_col.insert_many(quotes_to_insert)
            print(f"--- 成功匯入 {len(quotes_to_insert)} 條金句 ---")
        else:
            print("--- 沒有任何金句可匯入（可能 CSV 格式與預期不符，或書名在資料庫中不存在）---")
    finally:
        client.close()


if __name__ == "__main__":
    import_quotes(os.path.join("data", "quotes.csv"))
