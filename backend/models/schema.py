from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class Book(BaseModel):
    id: str = Field(alias="_id")
    title: str
    author: Optional[str] = None
    category: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    purchase_url: Optional[str] = None
    sample_link: Optional[str] = None

    class Config:
        populate_by_name = True


class Quote(BaseModel):
    id: str = Field(alias="_id")
    book_ref: Optional[str] = None
    content: str
    emotion_tags: List[str] = Field(default_factory=list)
    book_title: Optional[str] = None

    class Config:
        populate_by_name = True


class Character(BaseModel):
    id: str = Field(alias="_id")
    book_id: Optional[str] = None
    character_key: Optional[str] = None
    name: str
    description: Optional[str] = None
    personality_tags: Optional[str] = None
    image_url: Optional[str] = None

    class Config:
        populate_by_name = True


class Scene(BaseModel):
    id: str = Field(alias="_id")
    book_id: Optional[str] = None
    title: str
    description: str
    interaction_hint: Optional[str] = None
    scene_type: Optional[str] = "normal"

    class Config:
        populate_by_name = True


class QuizOption(BaseModel):
    option_id: str
    text: str
    character_scores: Dict[str, int] = Field(default_factory=dict)


class QuizQuestion(BaseModel):
    id: str = Field(alias="_id")
    quiz_id: Optional[str] = "default"
    question_text: str
    order: int = 1
    options: List[QuizOption] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class QuizResult(BaseModel):
    character_key: str
    character_name: str
    character_title: Optional[str] = None
    quote: Optional[str] = None
    analysis: Optional[str] = None
    mbti: Optional[str] = None
    traits: List[str] = Field(default_factory=list)


class MoodIntentOutput(BaseModel):
    mood: str = "neutral"
    intent: str = "general_chat"
    scene: str = "general"
    tone: str = "neutral"
    should_trigger_tool: bool = False


class QuoteBookOutput(BaseModel):
    book: Optional[Book] = None
    quote: Optional[Quote] = None
    reason: str
    confidence_score: float = 0.0


class QuizStoryOutput(BaseModel):
    interaction_id: str
    question: Optional[str] = None
    scene_title: Optional[str] = None
    description: Optional[str] = None
    interaction_hint: Optional[str] = None
    options: List[Dict[str, str]] = Field(default_factory=list)
    book_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class PreviewPurchaseOutput(BaseModel):
    book_id: str
    book_title: str
    purchase_url: Optional[str] = None
    sample_link: Optional[str] = None
    price_info: Optional[str] = None
    actions: List[Dict[str, str]] = Field(default_factory=list)


class StoryChoice(BaseModel):
    id: str = Field(alias="_id")
    scene_id: str
    text: str
    static_reply: Optional[str] = None
    next_scene_id: Optional[str] = None
    cta_text: Optional[str] = None
    buy_url: Optional[str] = None

    class Config:
        populate_by_name = True


class MemoryState(BaseModel):
    user_id: str
    detected_preferences: List[str] = Field(default_factory=list)
    recommended_book_ids: List[str] = Field(default_factory=list)
    recommended_quote_ids: List[str] = Field(default_factory=list)
    quiz_scores: Dict[str, int] = Field(default_factory=dict)
    current_scene_id: Optional[str] = None
    chat_history: List[Dict[str, str]] = Field(default_factory=list)


class UserRequest(BaseModel):
    user_id: str
    message: str
    interaction_id: Optional[str] = None
    current_book_id: Optional[str] = None
    timestamp: Optional[float] = None


class AgentResponse(BaseModel):
    text_content: str
    action_type: str
    data_payload: Optional[Dict[str, Any]] = None
    suggestions: List[str] = Field(default_factory=list)