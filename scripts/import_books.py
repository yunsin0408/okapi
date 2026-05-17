"""One-off script: import books from CSV into MongoDB (incremental upsert)."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne

load_dotenv(os.path.join(os.path.dirname(__file__), "../backend/.env"))


def process_and_import(csv_path: str) -> None:
    """Parse long-layout ``books.csv`` and upsert documents into MongoDB ``books``.

    First row is the header; each following row is one book. Required columns:
    ``title``, ``author``, ``purchase_url``, ``category``, ``summary``,
    ``sample_link``, ``tags``.

    Existing documents are preserved. Each row upserts by ``purchase_url`` when
    present; otherwise by ``title`` and ``author``.

    Args:
        csv_path: Path to ``books.csv``.
    """
    mongo_uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_BOOK_DATA", "okapi")

    if not mongo_uri:
        print("錯誤：找不到 MONGO_URI，請檢查 .env 檔案")
        return

    try:
        df = pd.read_csv(csv_path)
        required = {
            "title",
            "author",
            "purchase_url",
            "category",
            "summary",
            "sample_link",
            "tags",
        }
        if not required.issubset(set(df.columns)):
            print(
                "錯誤：CSV 缺少必要欄位 "
                f"{sorted(required)}，目前欄位為 {list(df.columns)}"
            )
            return

        books_to_insert: list[dict[str, Any]] = []

        print("--- 開始解析 CSV 資料 ---")
        for _, row in df.iterrows():
            title_raw = row["title"]
            if pd.isna(title_raw) or not str(title_raw).strip():
                continue
            if str(title_raw).strip() == "title":
                continue

            book_data = {
                "title": str(row["title"]).strip(),
                "author": str(row["author"]).strip() if pd.notna(row["author"]) else "Unknown",
                "purchase_url": (
                    str(row["purchase_url"]).strip()
                    if pd.notna(row["purchase_url"])
                    else ""
                ),
                "category": (
                    str(row["category"]).strip()
                    if pd.notna(row["category"])
                    else "其他"
                ),
                "summary": (
                    str(row["summary"]).strip() if pd.notna(row["summary"]) else ""
                ),
                "sample_link": (
                    str(row["sample_link"]).strip()
                    if pd.notna(row["sample_link"])
                    else ""
                ),
                "tags": [
                    t.strip()
                    for t in str(row["tags"]).split(",")
                    if t.strip()
                ]
                if pd.notna(row["tags"])
                else [],
            }
            books_to_insert.append(book_data)
            print(f"成功解析書籍: {book_data['title']}")

        if not books_to_insert:
            print("錯誤：無有效資料可匯入")
            return

        print("\n--- 正在連線至 MongoDB ---")
        client = MongoClient(mongo_uri)
        db = client[db_name]
        col = db["books"]

        operations: list[UpdateOne] = []
        for book in books_to_insert:
            purchase_url = str(book.get("purchase_url", "")).strip()
            if purchase_url:
                filt: dict[str, Any] = {"purchase_url": purchase_url}
            else:
                filt = {"title": book["title"], "author": book["author"]}
            operations.append(UpdateOne(filt, {"$set": book}, upsert=True))

        result = col.bulk_write(operations, ordered=False)
        print(
            "增量匯入完成："
            f"新增 {result.upserted_count} 筆、"
            f"更新 {result.modified_count} 筆、"
            f"比對到 {result.matched_count} 筆既有文件"
        )

        client.close()

    except FileNotFoundError:
        print(f"錯誤：找不到檔案 {csv_path}")
    except Exception as e:
        print(f"發生錯誤: {e}")


if __name__ == "__main__":
    DATA_PATH = os.path.join("data", "books.csv")
    process_and_import(DATA_PATH)
