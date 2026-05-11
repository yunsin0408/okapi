# okapi
# 目錄結構
```
book-agent-backend/
├── .env
├── main.py
├── requirements.txt
│
├── agents/
│   └── book_agent.py
│
├── core/
│   ├── config.py
│   ├── database.py
│   └── memory.py
│
├── tools/
│   ├── mood_intent_tool.py
│   ├── quote_book_tool.py
│   ├── quiz_story_tool.py
│   └── preview_purchase_tool.py
│
├── services/  
│   ├── llm_service.py
│   ├── mongo_service.py
│   ├── quote_service.py
│   ├── book_service.py
│   ├── story_service.py
│   └── character_service.py
│
├── models/
│   └── schema.py
│
└── scripts/
    └── embed_init.py
    └── import_books.py
```
1. 設定 Python 虛擬環境
```
python -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt
```