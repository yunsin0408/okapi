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
    personality_tags: str # mbti
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

# 1. 題目選項模型
class QuizOption(BaseModel):
    option_id: str
    text: str
    character_scores: Dict[str, int] # 靈活儲存如 {"romeo": 2}

# 2. 題目主體模型
class QuizQuestion(BaseModel):
    id: str = Field(alias="_id")
    quiz_id: str
    question_text: str
    order: int
    options: List[QuizOption]

    class Config:
        populate_by_name = True

# 3. 測驗結果模型 (用於最後產出分析報告)
class QuizResult(BaseModel):
    character_key: str
    character_name: str
    character_title: str
    quote: str
    analysis: str
    mbti: Optional[str]
    traits: List[str]

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

class StoryChoice(BaseModel):
    """選項表模型 (對應 choices collection)"""
    id: str = Field(alias="_id")
    scene_id: str
    text: str                   # 按鈕文字
    static_reply: str           # 點擊後的即時回饋
    next_scene_id: Optional[str] # 下一個場景
    cta_text: Optional[str]     # 導購按鈕文字 (選填)
    buy_url: Optional[str]      # 購買網址 (選填)

    class Config:
        populate_by_name = True

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
    user_id: str
    message: str                      # 無論打字或點按鈕，文字都放在這
    
    # 如果是從測驗或劇情按鈕點擊的，前端才需要帶這個 ID
    interaction_id: Optional[str] = None 
    
    current_book_id: Optional[str] = None
    timestamp: float

class AgentResponse(BaseModel):
    """後端最終回傳給前端的包裹"""
    text_content: str
    action_type: str   # "CHAT", "SHOW_QUOTE", "SHOW_BOOK", "SHOW_QUIZ", "SHOW_STORY"
    data_payload: Optional[Dict[str, Any]] = None
    suggestions: List[str] = [] # 快捷按鈕文字
