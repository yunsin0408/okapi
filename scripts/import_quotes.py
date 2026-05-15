"""One-off script: import quotes from CSV into MongoDB ``quotes`` (incremental upsert)."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne

load_dotenv()


def import_quotes(csv_path: str) -> None:
    """Parse long-layout ``quotes.csv`` and upsert into ``quotes`` after resolving ``book_ref``.

    First row is the header; each following row is one quote. Required columns:
    ``book_title``, ``content``. Optional: ``emotion_tags`` (comma-separated).

    Upserts by ``book_ref`` + ``content``. Quotes not in the CSV are left in the DB.

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

        df = pd.read_csv(csv_path)
        required = {"book_title", "content"}
        if not required.issubset(set(df.columns)):
            print(
                f"錯誤：CSV 缺少必要欄位 {sorted(required)}，目前欄位為 {list(df.columns)}"
            )
            return

        operations: list[UpdateOne] = []

        print("--- 開始關聯書籍 ID 並解析金句 ---")

        for _, row in df.iterrows():
            book_title_value = str(row["book_title"]).strip()
            if not book_title_value or book_title_value == "book_title":
                continue

            target_book = books_col.find_one({"title": book_title_value})
            if target_book:
                content = (
                    str(row["content"]).strip() if pd.notna(row["content"]) else ""
                )
                if not content:
                    print(f"警告：略過空白金句（書：{book_title_value}）")
                    continue
                emotion_tags: list[str] = []
                if "emotion_tags" in df.columns and pd.notna(row.get("emotion_tags")):
                    emotion_tags = [
                        tag.strip()
                        for tag in str(row["emotion_tags"]).split(",")
                        if tag.strip()
                    ]
                quote_data = {
                    "book_ref": target_book["_id"],
                    "book_title": target_book["title"],
                    "content": content,
                    "emotion_tags": emotion_tags,
                }
                filt: dict[str, Any] = {
                    "book_ref": quote_data["book_ref"],
                    "content": quote_data["content"],
                }
                operations.append(UpdateOne(filt, {"$set": quote_data}, upsert=True))
                print(f"成功關聯: {book_title_value}（金句已排入佇列）")
            else:
                print(
                    f"警告：找不到書名為 '{book_title_value}' 的書籍，請檢查 CSV 或先匯入 books"
                )

        if operations:
            result = quotes_col.bulk_write(operations, ordered=False)
            print(
                "--- 金句增量匯入完成："
                f"新增 {result.upserted_count} 筆、"
                f"更新 {result.modified_count} 筆、"
                f"比對到 {result.matched_count} 筆既有文件 ---"
            )
        else:
            print(
                "--- 沒有任何金句可匯入（可能 CSV 無資料列，或書名在資料庫中不存在）---"
            )
    finally:
        client.close()


if __name__ == "__main__":
    import_quotes(os.path.join("data", "quotes.csv"))
