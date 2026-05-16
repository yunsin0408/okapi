import os
import json
import logging
from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel
from openai import OpenAI
from core.config import settings

logger = logging.getLogger(__name__)

MOOD_INTENT_PROMPT = """
--- 系統角色與任務 ---
你是一個專業的「理解與推薦」核心模組。你的唯一任務是分析使用者最新的輸入文本，並根據預先定義的分類，精準判斷其情緒、意圖、情境與語氣。
你的分析結果將用於決定 Agent 的下一步動作，尤其是是否應立即觸發書籍推薦流程。

--- 輸入資訊 ---
使用者輸入 (User Query)：{user_query}
對話歷史摘要 (Context Summary)：{memory_summary} 
（如果 {memory_summary} 為空，則視為初次對話。）

--- 輸出格式規範 ---
你必須且只能輸出一個 JSON 物件，該物件必須完全符合 MoodIntentOutput Schema。
請根據以下定義的欄位進行輸出：

1.  mood (情緒)： 使用者當前的主導情緒（建議分類：興奮、平靜、低落、焦慮、無聊、憤怒、期待）。若無法判斷，填寫 "neutral"。
2.  intent (意圖)： 使用者發出此訊息的主要目的（請從以下類別選擇：recommendation, quiz, story, general_chat, greeting, memory_update, off_topic）。
3.  scene (情境)： 使用者可能處於的閱讀或生活情境（建議分類：通勤中、週末放鬆、工作壓力大、睡前、尋求知識、自我成長）。若無法判斷，填寫 "general"。
4.  tone (語氣)： 使用者使用的語氣風格（建議分類：正式、隨意、求助、抱怨、好奇、指令式）。
5.  should_trigger_recommendation (布林值)： 判斷 Agent 是否應立即呼叫推薦工具。
    -   如果 intent 是 'recommendation'、'quiz'、'story'，或情緒強烈（如低落、焦慮、憤怒）且需要內容輔助，則回傳 true。
    -   如果 intent 是 'greeting'、'general_chat'、'off_topic'，則回傳 false。

--- JSON 輸出範例（MoodIntentOutput Schema）---
```json
{{
  "mood": "低落",
  "intent": "recommendation",
  "scene": "工作壓力大",
  "tone": "求助",
  "should_trigger_recommendation": true
}}
"""

T = TypeVar('T', bound=BaseModel)

class LLMService:
    def __init__(self):
        api_key = settings.API_KEY or os.getenv("HF_TOKEN")
        
        base_url = "https://router.huggingface.co/v1" if os.getenv("HF_TOKEN") else None
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.default_model = "yentinglin/Llama-3-Taiwan-70B-Instruct:featherless-ai" if base_url else "gpt-4o-mini"

    def generate_json(self, system_prompt: str, user_prompt: str, response_model: Type[T], model: Optional[str] = None) -> T:
        model = model or self.default_model
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        for attempt in range(3):
            try:
                completion = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=1024,
                    temperature=0.1,
                )
                
                content = completion.choices[0].message.content.strip()
                
                if content.startswith("```json"):
                    content = content[7:-3].strip()
                elif content.startswith("```"):
                    content = content[3:-3].strip()
                    
                parsed_json = json.loads(content)
                return response_model(**parsed_json)
            except Exception as e:
                logger.warning(f"LLM JSON generation failed on attempt {attempt + 1}: {e}")
                if attempt == 2:
                    raise RuntimeError(f"Failed to generate valid JSON after 3 attempts. Error: {e}")

llm_service = LLMService()
