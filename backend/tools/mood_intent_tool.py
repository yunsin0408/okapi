import logging
# 修正路徑與變數
from services.llm_service import llm_service, MOOD_INTENT_PROMPT
from models.schema import MoodIntentOutput 

logger = logging.getLogger(__name__)

class MoodIntentTool:
    """
    核心邏輯工具：呼叫 LLM 判斷使用者情緒與意圖，
    並決定是否需要進入後續的書籍金句推薦流程。
    """
    
    def analyze(self, user_input: str) -> MoodIntentOutput:
        logger.info(f"Analyzing mood and intent for input: {user_input}")
        try:
            # 🚀 【架構師微調】：在使用者丟出的話後面，強行補上「嚴厲指令」，逼大佛一定要吐出完美 JSON
            strict_user_prompt = (
                f"{user_input}\n\n"
                "⚠️ 請務必嚴格遵守 JSON Schema 格式輸出，不要包含任何開頭、結尾的解釋字串與 ```json 標籤！"
            )
            
            return llm_service.generate_json(
                system_prompt=MOOD_INTENT_PROMPT,
                user_prompt=strict_user_prompt,
                response_model=MoodIntentOutput
            )
        except Exception as e:
            logger.error(f"Failed to analyze mood and intent: {e}")
            # 🚀 【架構師核心修正】：徹底修正備用便當盒！
            # 完美補齊 urgency 與 should_trigger_tool，把舊的 is_recommendation_needed 碎屍萬段！
            return MoodIntentOutput(
                mood="neutral", 
                intent="general_chat", 
                scene="general", 
                tone="neutral", 
                should_trigger_tool=False       # 🟢 補齊這個格子
            )

mood_intent_tool = MoodIntentTool()
