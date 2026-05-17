"""
main.py
======
FastAPI 後端入口。

A 組負責重點：
1. 定義 API routes（例如 /chat）
2. 驗證前端傳來的 request 格式
3. 把使用者輸入交給 BookAgent
4. 把 BookAgent 的結果回傳給前端

注意：main.py 不寫推薦邏輯、不查資料庫、不直接呼叫各種 tool。
真正的流程控制放在 agents/book_agent.py。
"""

from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from agents.book_agent import BookAgent


# 建立 FastAPI app。title/version 會顯示在 http://127.0.0.1:8000/docs
app = FastAPI(
    title="Book Agent Backend",
    version="0.3.0"
)

# 建立全域 BookAgent 實例。
# Server 啟動後，所有 /chat request 都會使用這個 Agent 來處理。
book_agent = BookAgent()


class ChatRequest(BaseModel):
    """
    前端呼叫 POST /chat 時要送來的資料格式。

    user_id：必填，用來辨識是哪個使用者。
    message：必填，使用者輸入的文字或點擊選項的文字。
    interaction_id：選填，如果正在進行測驗/故事，前端可以帶這個欄位。
    current_book_id：選填，如果使用者目前正在看某本書，前端可以帶這個欄位。
    """

    user_id: str = Field(..., min_length=1, description="使用者 ID")
    message: str = Field(..., min_length=1, description="使用者輸入內容")
    interaction_id: Optional[str] = Field(None, description="互動流程 ID，例如測驗或故事")
    current_book_id: Optional[str] = Field(None, description="目前選到的書籍 ID")


@app.get("/")
def root():
    """
    首頁健康提示。
    用來快速確認後端是否有正常啟動。
    """
    return {
        "status": "ok",
        "message": "Book Agent Backend Running",
        "available_routes": ["/chat", "/health", "/docs"]
    }


@app.get("/health")
def health_check():
    """
    健康檢查 API。
    之後如果要部署到雲端、Docker 或給前端測連線，可以用這支。
    """
    return {
        "status": "healthy",
        "service": "book-agent-backend",
        "version": "0.3.0"
    }


@app.post("/chat")
def chat(request: ChatRequest):
    """
    聊天主 API。

    流程：
    1. FastAPI + Pydantic 先檢查 request 格式
    2. 把資料丟給 BookAgent.run()
    3. 回傳 BookAgent 統一整理好的 response
    """

    result = book_agent.run(
        user_id=request.user_id,
        user_input=request.message,
        interaction_id=request.interaction_id,
        current_book_id=request.current_book_id
    )

    return result
