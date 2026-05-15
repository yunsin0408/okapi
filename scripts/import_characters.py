"""One-off script: import characters from CSV into MongoDB ``characters``."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne

load_dotenv()


def import_characters(csv_path: str) -> None:
    """Import rows from ``characters.csv`` into ``characters`` with ``book_id`` resolved.

    ``data/characters.csv`` is a **long table** (same convention as ``books.csv`` /
    ``quotes.csv``): first row is the header ``book_title,name,description,mbti``;
    each following row is one character.

    Mongo documents follow ``Character`` in ``book-agent-backend/models/schema.py``:
    ``book_id``, ``name``, ``description``, ``personality_tags`` (from ``mbti`` cell),
    optional ``image_url``.

    Upserts by ``book_id`` + ``name`` so re-runs update the same character without
    wiping the whole collection.

    Args:
        csv_path: Path to ``characters.csv``.
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
        chars_col = db["characters"]

        # Long-table CSV: header row + one row per character
        df = pd.read_csv(csv_path)

        required = {"book_title", "name", "description"}
        if not required.issubset(set(df.columns)):
            print(
                f"錯誤：CSV 缺少必要欄位 {sorted(required)}，目前欄位為 {list(df.columns)}"
            )
            return

        print("--- 開始關聯書籍 ID 並解析角色資料 ---")

        operations: list[UpdateOne] = []
        for _, row in df.iterrows():
            book_title_value = str(row["book_title"]).strip()
            if not book_title_value or book_title_value == "book_title":
                continue

            target_book = books_col.find_one({"title": book_title_value})
            if not target_book:
                print(f"警告：找不到書名為 '{book_title_value}' 的書籍，請檢查 CSV 或先匯入 books")
                continue

            name = str(row["name"]).strip() if pd.notna(row["name"]) else "Unknown"
            description = (
                str(row["description"]).strip() if pd.notna(row["description"]) else ""
            )
            mbti_raw = row["mbti"] if "mbti" in df.columns else None
            mbti = str(mbti_raw).strip() if pd.notna(mbti_raw) else ""
            personality_tags: list[str] = [mbti] if mbti else []

            image_url: str | None = None
            if "image_url" in df.columns and pd.notna(row.get("image_url")):
                s = str(row["image_url"]).strip()
                image_url = s if s else None

            book_id = target_book["_id"]
            char_doc: dict[str, Any] = {
                "book_id": book_id,
                "name": name,
                "description": description,
                "personality_tags": personality_tags,
                "image_url": image_url,
            }
            filt: dict[str, Any] = {"book_id": book_id, "name": name}
            operations.append(UpdateOne(filt, {"$set": char_doc}, upsert=True))
            print(f"成功關聯: {book_title_value} -> 角色: {name}")

        if operations:
            result = chars_col.bulk_write(operations, ordered=False)
            print(
                "--- 角色增量匯入完成："
                f"新增 {result.upserted_count} 筆、"
                f"更新 {result.modified_count} 筆、"
                f"比對到 {result.matched_count} 筆既有文件 ---"
            )
        else:
            print("--- 沒有任何角色資料可匯入 ---")
    finally:
        client.close()


if __name__ == "__main__":
    import_characters(os.path.join("data", "characters.csv"))
