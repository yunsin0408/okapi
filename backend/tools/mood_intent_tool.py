import logging
from backend.services.llm_service import llm_service, MOOD_INTENT_PROMPT_TEMPLATE
from backend.models.schema import MoodIntentOutput # 依賴 B 區塊定義的 Schema

logger = logging.getLogger(__name__)

class MoodIntentTool:
    """
    核心邏輯工具：呼叫 LLM 判斷使用者情緒與意圖，
    並決定是否需要進入後續的書籍金句推薦流程。
    """
    
    def analyze(self, user_input: str) -> MoodIntentOutput:
        logger.info(f"Analyzing mood and intent for input: {user_input}")
        try:
            return llm_service.generate_json(
                system_prompt=MOOD_INTENT_PROMPT_TEMPLATE,
                user_prompt=user_input,
                response_model=MoodIntentOutput
            )
        except Exception as e:
            logger.error(f"Failed to analyze mood and intent: {e}")
            # Fallback
            return MoodIntentOutput(
                mood="neutral", intent="chat", scene="general", tone="neutral", is_recommendation_needed=False
            )

mood_intent_tool = MoodIntentTool()