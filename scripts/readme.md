# 腳本說明

本目錄放一次性或維運用腳本。以下說明如何在本機執行，方便重現相同步驟。

---

## 事前準備

### 1. 環境變數 `.env`

在專案根目錄建立或編輯 `.env`

| 變數 | 必填 | 說明 |
|------|------|------|
| `MONGO_URI` | 是 | Atlas 連線字串，格式如 `mongodb+srv://使用者:密碼@cluster...`。 |
| `DB_BOOK_DATA` | 否 | MongoDB **資料庫名稱**。未設定時腳本預設為 `okapi`。 |

### 2. MongoDB Atlas（團隊共用叢集時）

- **Network Access**：將你目前對外 IP 加入允許清單（或依團隊規範設定）。
- **Database Access**：使用「資料庫使用者」帳密，不是登入 Atlas 網站的 Email。

連線是否正常，可在專案根目錄執行（需已啟用 venv 並安裝依賴）：

```bash
python <<'PY'
import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(".env"))
uri = os.environ["MONGO_URI"]
client = MongoClient(uri, serverSelectionTimeoutMS=15000)
client.admin.command("ping")
print("ping OK")
client.close()
PY
```

---

## `import_books.py`：將 `data/books.csv` 匯入 MongoDB

### 功能

- 讀取專案根目錄下的 **`data/books.csv`**，解析後寫入 MongoDB 集合 **`books`**。
- **增量匯入**：不會清空集合；同一本書再次匯入會**更新**而非重複插入。
- **比對鍵**：有 **`purchase_url`**（非空白）時以網址比對；否則以 **`title` + `author`** 比對。

### CSV 格式（重要）

表格為「**寬表**」：第一欄為欄位名稱，每一欄往右代表一本書。必填欄位名稱（第一欄文字）須包含：

`title`、`author`、`purchase_url`、`category`、`summary`、`sample_link`、`tags`

- `tags`：字串內以英文逗號 `,` 分隔多個標籤，匯入後為陣列。

試算表可照下圖排版（A 欄為欄位名，往右每一欄一本書）；編輯完成後匯出為 CSV，對應 `data/books.csv` 即可。

![試算表寬表範例（A 欄欄位名，B／C 欄為兩本書）](spreadsheet.png)

### 執行方式

**在專案根目錄執行**（腳本使用相對路徑 `data/books.csv`）：

```bash
cd /path/to/okapi         
source .venv/bin/activate
python scripts/import_books.py
```

### 成功時輸出

終端機會列出解析到的書名，最後出現類似：

`增量匯入完成：新增 N 筆、更新 M 筆、比對到 K 筆既有文件`

