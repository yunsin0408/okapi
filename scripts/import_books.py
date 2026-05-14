"""One-off script: import books from CSV into MongoDB (incremental upsert)."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne

load_dotenv()


def process_and_import(csv_path: str) -> None:
    """Parse the transposed books CSV and upsert documents into MongoDB ``books``.

    Existing documents are preserved. Each row upserts by ``purchase_url`` when
    present; otherwise by ``title`` and ``author`` so re-imports update the same
    logical book instead of appending duplicates.

    Args:
        csv_path: Path to ``books.csv`` (wide layout: field names in column 0).
    """
    # 從 .env 取得連線資訊
    mongo_uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_BOOK_DATA", "okapi")
    
    if not mongo_uri:
        print("錯誤：找不到 MONGO_URI，請檢查 .env 檔案")
        return

    try:
        # 2. 讀取並處理 CSV (轉置邏輯)
        # 根據表格結構，第一欄為欄位名稱，資料向右延伸
        df = pd.read_csv(csv_path, header=None)
        df = df.set_index(0).T
        
        books_to_insert = []
        
        print("--- 開始解析 CSV 資料 ---")
        for index, row in df.iterrows():
            # 對齊規定的欄位名稱
            book_data = {
                "title": str(row['title']).strip() if pd.notna(row['title']) else "Unknown",
                "author": str(row['author']).strip() if pd.notna(row['author']) else "Unknown",
                "purchase_url": str(row['purchase_url']).strip() if pd.notna(row['purchase_url']) else "",
                "category": str(row['category']).strip() if pd.notna(row['category']) else "其他",
                "summary": str(row['summary']).strip() if pd.notna(row['summary']) else "",
                "sample_link": str(row['sample_link']).strip() if pd.notna(row['sample_link']) else "",
                # 處理 Tags：依據規範轉為 Array 格式
                "tags": [t.strip() for t in str(row['tags']).split(',')] if pd.notna(row['tags']) else []
            }
            books_to_insert.append(book_data)
            print(f"成功解析書籍: {book_data['title']}")

        if not books_to_insert:
            print("錯誤：無有效資料可匯入")
            return

        # 3. 建立連線並匯入
        print(f"\n--- 正在連線至 MongoDB ---")
        client = MongoClient(mongo_uri)
        db = client[db_name]
        col = db["books"]

        # Incremental upsert: do not delete existing docs. Dedupe by purchase_url,
        # or by title+author when purchase_url is empty.
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
    # 設定 CSV 檔案路徑
    DATA_PATH = os.path.join("data", "books.csv")
    process_and_import(DATA_PATH)