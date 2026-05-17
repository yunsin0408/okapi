from fastapi import FastAPI
from pydantic import BaseModel

from agents.book_agent import BookAgent

app = FastAPI(
    title="Book Agent Backend",
    version="0.1.0"
)

book_agent = BookAgent()


class ChatRequest(BaseModel):
    user_id: str
    message: str


@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Book Agent Backend Running"
    }


@app.post("/chat")
def chat(request: ChatRequest):

    result = book_agent.run(
        user_id=request.user_id,
        user_input=request.message
    )

    return result