from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# ==========================================
# 1. 基礎資料單元 (對應 MongoDB Collection)
# ==========================================

class Book(BaseModel):
    """書籍主表"""
    id: str = Field(alias="_id")
    title: str
    author: str
    category: str
    summary: str
    tags: List[str]     
    purchase_url: str
    sample_link: str

    class Config:
        populate_by_name = True

class Quote(BaseModel):
    """金句表"""
    id: str = Field(alias="_id")
    book_ref: str        # 關聯到 Book._id
    content: str
    emotion_tags: List[str]   
    book_title: str

    class Config:
        populate_by_name = True

class Character(BaseModel):
    """角色資料表"""
    id: str = Field(alias="_id")
    book_id: str                # 關聯到 Book._id
    name: str
    description: str
    personality_tags: List[str] # 例如 ["樂觀", "謹慎"]
    image_url: Optional[str] = None

    class Config:
        populate_by_name = True

class Scene(BaseModel):
    """劇情場景表"""
    id: str = Field(alias="_id")
    book_id: str         # 關聯到 Book._id
    title: str
    description: str
    interaction_hint: str
    scene_type: str      # "normal" 或 "ending"

class QuizStory(BaseModel):
    """測驗"""
    scene_title: str
    description: str
    interaction_hint: str
    options: List[Dict[str, str]] # [{"id": "A", "text": "走向他"}]
    book_id: str

    class Config:
        populate_by_name = True

# ==========================================
# 2. 中層分析與工具輸出 (對應 Tools & Services)
# ==========================================

class MoodIntentOutput(BaseModel):
    """C 組 mood_intent_tool 輸出"""
    mood: str
    intent: str
    urgency: int = Field(ge=1, le=5)
    should_trigger_tool: bool

class QuoteBookOutput(BaseModel):
    """C 組 quote_book_tool 輸出"""
    selected_quote: Quote
    recommended_book_id: str
    reason: str
    confidence_score: float = 0.0 # 讓 Agent 判斷推薦強度

class QuizStoryOutput(BaseModel):
    """D 組 quiz_story_tool 輸出"""
    scene_title: str
    description: str
    interaction_hint: str
    options: List[Dict[str, str]] # [{"id": "A", "text": "走向他"}]
    book_id: str

class PreviewPurchaseOutput(BaseModel):
    """D 組 preview_purchase_tool 輸出"""
    book_title: str
    purchase_url: str
    sample_link: str
    price_info: Optional[str] = None

# ==========================================
# 3. 系統狀態與通訊 (對應 Agent & Frontend)
# ==========================================

class MemoryState(BaseModel):
    """系統長期記憶 (存於 core/memory.py)"""
    user_id: str
    detected_preferences: List[str] = []
    recommended_book_ids: List[str] = []
    quiz_scores: Dict[str, int] = {}
    current_scene_id: Optional[str] = None

class UserRequest(BaseModel):
    """前端傳入的請求"""
    user_id: str
    message: str
    current_book_id: Optional[str] = None

class AgentResponse(BaseModel):
    """後端最終回傳給前端的包裹"""
    text_content: str
    action_type: str   # "CHAT", "SHOW_QUOTE", "SHOW_BOOK", "SHOW_QUIZ", "SHOW_STORY"
    data_payload: Optional[Dict[str, Any]] = None
    suggestions: List[str] = [] # 快捷按鈕文字
