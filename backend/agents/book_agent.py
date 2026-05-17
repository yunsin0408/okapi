class BookAgent:

    def __init__(self):

        print("Book Agent initialized")

    # ====================================
    # Main Flow
    # ====================================

    def run(
        self,
        user_id: str,
        user_input: str
    ):

        # Step 1
        mood_result = self.analyze_mood_and_intent(
            user_input
        )

        # Step 2
        route = self.decide_route(
            mood_result
        )

        # Step 3
        tool_result = self.execute_route(
            route,
            user_input
        )

        # Step 4
        final_response = self.build_response(
            mood_result,
            tool_result
        )

        return final_response

    # ====================================
    # Mood / Intent Analysis
    # ====================================

    def analyze_mood_and_intent(
        self,
        user_input: str
    ):

        text = user_input.lower()

        if "累" in text:

            return {
                "emotion": "tired",
                "intent": "comfort"
            }

        elif "推薦" in text:

            return {
                "emotion": "neutral",
                "intent": "recommend"
            }

        elif "測驗" in text:

            return {
                "emotion": "playful",
                "intent": "quiz"
            }

        elif "故事" in text:

            return {
                "emotion": "immersive",
                "intent": "story"
            }

        return {
            "emotion": "unknown",
            "intent": "fallback"
        }

    # ====================================
    # Route Decision
    # ====================================

    def decide_route(
        self,
        mood_result: dict
    ):

        intent = mood_result["intent"]

        if intent == "comfort":
            return "quote_book"

        elif intent == "recommend":
            return "book_recommendation"

        elif intent == "quiz":
            return "quiz"

        elif intent == "story":
            return "story"

        return "fallback"

    # ====================================
    # Execute Tool
    # ====================================

    def execute_route(
        self,
        route: str,
        user_input: str
    ):

        # 未來會真正呼叫 tool

        if route == "quote_book":

            return {
                "type": "quote_book",
                "quote": "痛苦也是人生的一部分。",
                "book": "被討厭的勇氣"
            }

        elif route == "book_recommendation":

            return {
                "type": "book_recommendation",
                "books": [
                    "原子習慣",
                    "人性的弱點"
                ]
            }

        elif route == "quiz":

            return {
                "type": "quiz",
                "question": "你遇到困難時會怎麼做？"
            }

        elif route == "story":

            return {
                "type": "story",
                "scene": "你走進了一間神秘書店..."
            }

        return {
            "type": "fallback",
            "reply": "我還在學習怎麼推薦書籍給你。"
        }

    # ====================================
    # Final Response
    # ====================================

    def build_response(
        self,
        mood_result: dict,
        tool_result: dict
    ):

        return {
            "emotion": mood_result["emotion"],
            "intent": mood_result["intent"],
            "result": tool_result
        }