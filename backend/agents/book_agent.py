"""
book_agent.py
=============
A 組負責的 Agent Orchestrator（總控台）。

這份檔案的設計目標：
1. 有工具完成時：優先呼叫真正的 tool/service。
2. 工具還沒完成、import 失敗、資料庫還沒接、LLM 沒 API key 時：自動改跑 mock 模擬資料。
3. 對前端永遠回傳統一格式，避免前端因為某個工具壞掉就不能測。
4. 保留清楚註解，方便之後把 mock 區塊替換成正式工具。
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List, Callable
from difflib import get_close_matches

logger = logging.getLogger(__name__)


class BookAgent:
    """
    BookAgent 是整個後端聊天流程的總控台，不是單一推薦工具。

    它負責：
    1. 接收 main.py 傳進來的使用者訊息
    2. 做基本輸入檢查與錯誤防呆
    3. 分析情緒與意圖
    4. 決定要走哪一條 route
    5. 優先呼叫已完成工具；如果工具不可用，就使用 mock fallback
    6. 統一整理成前端可用的 response 格式
    """

    def __init__(self):
        """
        初始化 Agent。

        這裡會嘗試載入其他組已經寫好的工具。
        如果工具還沒寫好、檔案是空的、import 錯誤、schema 對不起來，
        系統不會直接掛掉，而是把該工具標記成 unavailable，之後自動跑 mock。
        """

        self.tool_status: Dict[str, bool] = {
            "mood_intent": False,
            "quote_book": False,
            "quiz_story": False,
            "preview_purchase": False,
            "story": False,
        }

        self.mood_intent_tool = self._safe_import_tool(
            tool_name="mood_intent",
            import_func=self._import_mood_intent_tool,
        )
        self.quote_book_tool = self._safe_import_tool(
            tool_name="quote_book",
            import_func=self._import_quote_book_tool,
        )
        self.quiz_story_tool = self._safe_import_tool(
            tool_name="quiz_story",
            import_func=self._import_quiz_story_tool,
        )
        self.preview_purchase_tool = self._safe_import_tool(
            tool_name="preview_purchase",
            import_func=self._import_preview_purchase_tool,
        )

        print("Book Agent initialized")
        print(f"Tool status: {self.tool_status}")

    # ------------------------------------------------------------------
    # Tool import 區：所有 import 都集中在這裡，避免工具未完成時整個後端掛掉
    # ------------------------------------------------------------------

    def _safe_import_tool(self, tool_name: str, import_func: Callable[[], Any]) -> Any:
        """
        安全載入工具。

        如果成功：回傳工具物件，並把 tool_status[tool_name] 設為 True。
        如果失敗：回傳 None，並保留 False，之後 execute_route 會自動跑 mock。
        """
        try:
            tool = import_func()
            if tool is not None:
                self.tool_status[tool_name] = True
            return tool
        except Exception as exc:
            logger.warning("Tool %s unavailable, fallback to mock. Error: %s", tool_name, exc)
            self.tool_status[tool_name] = False
            return None

    def _import_mood_intent_tool(self):
        # 目前 mood_intent_tool.py 裡有 backend.services 的 import，
        # 在不同啟動位置可能會失敗，所以用 try 包住。
        try:
            from tools.mood_intent_tool import mood_intent_tool
            return mood_intent_tool
        except Exception:
            from backend.tools.mood_intent_tool import mood_intent_tool
            return mood_intent_tool

    def _import_quote_book_tool(self):
        try:
            from tools.quote_book_tool import quote_book_tool
            return quote_book_tool
        except Exception:
            from backend.tools.quote_book_tool import quote_book_tool
            return quote_book_tool

    def _import_quiz_story_tool(self):
        """
        quiz_story_tool.py 目前在壓縮檔中是空的。
        如果之後 D 組完成並提供 quiz_story_tool 物件，這裡就會自動吃到。
        """
        try:
            from tools.quiz_story_tool import quiz_story_tool
            return quiz_story_tool
        except Exception:
            from backend.tools.quiz_story_tool import quiz_story_tool
            return quiz_story_tool

    def _import_preview_purchase_tool(self):
        """
        preview_purchase_tool.py 目前在壓縮檔中是空的。
        如果之後 D 組完成並提供 preview_purchase_tool 物件，這裡就會自動吃到。
        """
        try:
            from tools.preview_purchase_tool import preview_purchase_tool
            return preview_purchase_tool
        except Exception:
            from backend.tools.preview_purchase_tool import preview_purchase_tool
            return preview_purchase_tool

    # ------------------------------------------------------------------
    # Main Flow：main.py 只會呼叫這個 run()
    # ------------------------------------------------------------------

    def run(
        self,
        user_id: str,
        user_input: str,
        interaction_id: Optional[str] = None,
        current_book_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Agent 主流程。

        固定順序：
        1. validate_user_input：先檢查使用者輸入是否合理
        2. analyze_mood_and_intent：分析情緒與意圖
        3. detect_possible_confusion：偵測可能的書名打錯或語意模糊
        4. decide_route：決定 route
        5. execute_route：呼叫工具；工具未完成就跑 mock
        6. build_response：整理成前端統一格式
        """

        validation = self.validate_user_input(user_input)
        if not validation["is_valid"]:
            return self.build_response(
                route="fallback",
                mood_intent=self.default_mood_intent(),
                tool_result={
                    "type": "input_error",
                    "text": validation["message"],
                    "error_code": validation["error_code"],
                },
                debug={"tool_status": self.tool_status},
            )

        mood_intent = self.analyze_mood_and_intent(user_input)
        confusion_info = self.detect_possible_confusion(user_input, current_book_id)
        route = self.decide_route(mood_intent, interaction_id, confusion_info)

        tool_result = self.execute_route(
            route=route,
            user_id=user_id,
            user_input=user_input,
            mood_intent=mood_intent,
            interaction_id=interaction_id,
            current_book_id=current_book_id,
            confusion_info=confusion_info,
        )

        return self.build_response(
            route=route,
            mood_intent=mood_intent,
            tool_result=tool_result,
            debug={
                "tool_status": self.tool_status,
                "used_mock": tool_result.get("mock", False),
                "confusion_info": confusion_info,
            },
        )

    # ------------------------------------------------------------------
    # 1. 使用者輸入檢查：A 組需要做基本防呆，但不需要做所有內容理解
    # ------------------------------------------------------------------

    def validate_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        檢查使用者輸入是否可以處理。

        這部分屬於 A 組 main/agent 應該做的「入口防呆」。
        例如：空字串、太長、純符號。

        更進階的「書名相似搜尋」、「資料庫查不到」、「語意不清楚」可以由：
        - services/book_service.py
        - tools/quote_book_tool.py
        - tools/mood_intent_tool.py
        協作完成。
        但 Agent 這裡可以先做一層簡單判斷。
        """

        if user_input is None:
            return {
                "is_valid": False,
                "error_code": "EMPTY_INPUT",
                "message": "我沒有收到你的訊息，可以再輸入一次嗎？",
            }

        cleaned = user_input.strip()

        if not cleaned:
            return {
                "is_valid": False,
                "error_code": "EMPTY_INPUT",
                "message": "你剛剛好像沒有輸入內容，可以告訴我你想找什麼書嗎？",
            }

        if len(cleaned) > 500:
            return {
                "is_valid": False,
                "error_code": "INPUT_TOO_LONG",
                "message": "你的訊息有點太長了，可以先用一兩句話告訴我你想找哪類書嗎？",
            }

        # 如果幾乎都是標點符號，通常無法判斷意圖。
        meaningful_chars = [ch for ch in cleaned if ch.isalnum() or "\u4e00" <= ch <= "\u9fff"]
        if len(meaningful_chars) == 0:
            return {
                "is_valid": False,
                "error_code": "NO_MEANINGFUL_TEXT",
                "message": "我看不太懂這段內容，可以用文字描述你想找的書或心情嗎？",
            }

        return {"is_valid": True, "error_code": None, "message": "ok"}

    # ------------------------------------------------------------------
    # 2. 情緒與意圖分析：有工具就用工具；工具壞掉就用 rule-based mock
    # ------------------------------------------------------------------

    def default_mood_intent(self) -> Dict[str, Any]:
        """預設情緒意圖。當分析失敗時使用。"""
        return {
            "mood": "neutral",
            "intent": "general_chat",
            "scene": "general",
            "tone": "neutral",
            "should_trigger_tool": False,
            "source": "default",
        }

    def analyze_mood_and_intent(self, user_input: str) -> Dict[str, Any]:
        """
        分析使用者情緒與意圖。

        優先順序：
        1. 如果 mood_intent_tool 可用，就呼叫真正 LLM 工具。
        2. 如果工具不可用或呼叫失敗，就使用本檔案內建的關鍵字 fallback。
        """

        if self.mood_intent_tool is not None:
            try:
                # 目前 mood_intent_tool 的 method 叫 analyze()
                result = self.mood_intent_tool.analyze(user_input)
                return self._normalize_mood_intent(result, source="tool")
            except Exception as exc:
                logger.warning("MoodIntentTool failed, fallback to mock: %s", exc)

        return self.mock_analyze_mood_and_intent(user_input)

    def _normalize_mood_intent(self, result: Any, source: str) -> Dict[str, Any]:
        """
        把工具回傳的 Pydantic model 或 dict 統一轉成 Agent 內部使用的 dict。

        這很重要，因為目前 schema.py 和 mood_intent_tool.py 欄位還有點不一致：
        有的叫 should_trigger_tool，有的 prompt 寫 should_trigger_recommendation。
        這裡統一轉成 should_trigger_tool。
        """

        if hasattr(result, "model_dump"):
            data = result.model_dump()
        elif hasattr(result, "dict"):
            data = result.dict()
        elif isinstance(result, dict):
            data = result
        else:
            data = {}

        return {
            "mood": data.get("mood", "neutral"),
            "intent": data.get("intent", "general_chat"),
            "scene": data.get("scene", "general"),
            "tone": data.get("tone", "neutral"),
            "should_trigger_tool": data.get(
                "should_trigger_tool",
                data.get("should_trigger_recommendation", False),
            ),
            "source": source,
        }

    def mock_analyze_mood_and_intent(self, user_input: str) -> Dict[str, Any]:
        """
        模擬版情緒/意圖分析。

        這裡不用 LLM，只用關鍵字判斷。
        好處是：就算 LLM API key 沒設定、工具還沒完成，也能讓前端和 API 繼續測。
        """

        text = user_input.lower().strip()

        if any(keyword in text for keyword in ["累", "壓力", "難過", "焦慮", "煩", "低落", "迷茫", "撐不下去"]):
            return {
                "mood": "低落",
                "intent": "recommendation",
                "scene": "情緒陪伴",
                "tone": "求助",
                "should_trigger_tool": True,
                "source": "mock_rule",
            }

        if any(keyword in text for keyword in ["測驗", "人格", "適合哪本", "我是誰", "角色"]):
            return {
                "mood": "好奇",
                "intent": "quiz",
                "scene": "互動測驗",
                "tone": "好奇",
                "should_trigger_tool": True,
                "source": "mock_rule",
            }

        if any(keyword in text for keyword in ["故事", "劇情", "互動", "冒險", "沉浸"]):
            return {
                "mood": "沉浸",
                "intent": "story",
                "scene": "互動故事",
                "tone": "好奇",
                "should_trigger_tool": True,
                "source": "mock_rule",
            }

        if any(keyword in text for keyword in ["購買", "試讀", "連結", "哪裡買", "買", "價格"]):
            return {
                "mood": "neutral",
                "intent": "preview_purchase",
                "scene": "購買導流",
                "tone": "指令式",
                "should_trigger_tool": True,
                "source": "mock_rule",
            }

        if any(keyword in text for keyword in ["推薦", "想看", "書", "適合", "找一本", "有沒有"]):
            return {
                "mood": "neutral",
                "intent": "recommendation",
                "scene": "找書推薦",
                "tone": "求助",
                "should_trigger_tool": True,
                "source": "mock_rule",
            }

        if any(keyword in text for keyword in ["嗨", "哈囉", "你好", "hello", "hi"]):
            return {
                "mood": "neutral",
                "intent": "greeting",
                "scene": "general",
                "tone": "隨意",
                "should_trigger_tool": False,
                "source": "mock_rule",
            }

        return self.default_mood_intent() | {"source": "mock_rule"}

    # ------------------------------------------------------------------
    # 3. 模糊/錯誤輸入偵測：先做基本版，之後可搬到 book_service 做資料庫版
    # ------------------------------------------------------------------

    def detect_possible_confusion(
        self,
        user_input: str,
        current_book_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        偵測使用者是否可能：
        1. 書名打錯
        2. 表達太模糊
        3. 前後文可能接不起來

        這裡先用 mock 書名清單做簡單偵測。
        正式版應該交給 book_service，從 MongoDB 的 books collection 查詢。
        """

        known_titles = [
            "被討厭的勇氣",
            "原子習慣",
            "人性的弱點",
            "小王子",
            "解憂雜貨店",
            "蛤蟆先生去看心理師",
            "活著",
        ]

        text = user_input.strip()
        close_matches = get_close_matches(text, known_titles, n=3, cutoff=0.55)

        # 使用者只輸入很短、很籠統的內容，通常需要追問。
        vague_words = ["隨便", "都可以", "不知道", "不清楚", "看心情", "推薦一下"]
        is_vague = any(word in text for word in vague_words) or len(text) <= 2

        # 有 current_book_id 但使用者突然講購買以外的完全不同需求，可能前後文斷裂。
        context_mismatch = bool(current_book_id and any(word in text for word in ["換", "不要", "不是", "其他", "重新"])
        )

        return {
            "is_vague": is_vague,
            "possible_title_matches": close_matches,
            "context_mismatch": context_mismatch,
            "current_book_id": current_book_id,
        }

    # ------------------------------------------------------------------
    # 4. Route Decision：決定要走哪個工具/流程
    # ------------------------------------------------------------------

    def decide_route(
        self,
        mood_intent: Dict[str, Any],
        interaction_id: Optional[str] = None,
        confusion_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        根據情緒意圖和互動狀態決定路由。

        route 是 Agent 內部使用的流程名稱，不一定等於前端 action_type。
        """

        confusion_info = confusion_info or {}

        if confusion_info.get("is_vague"):
            return "clarify"

        if confusion_info.get("context_mismatch"):
            return "clarify_context"

        # 如果有 interaction_id，代表使用者正在測驗或故事流程中，先續接原流程。
        if interaction_id:
            return "continue_interaction"

        intent = mood_intent.get("intent", "general_chat")

        if intent in ["recommendation", "comfort"]:
            return "quote_book"

        if intent == "quiz":
            return "quiz_story"

        if intent == "story":
            return "story"

        if intent == "preview_purchase":
            return "preview_purchase"

        if intent == "greeting":
            return "greeting"

        return "fallback"

    # ------------------------------------------------------------------
    # 5. Execute Route：有工具用工具，工具不能用就用 mock
    # ------------------------------------------------------------------

    def execute_route(
        self,
        route: str,
        user_id: str,
        user_input: str,
        mood_intent: Dict[str, Any],
        interaction_id: Optional[str] = None,
        current_book_id: Optional[str] = None,
        confusion_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        執行指定 route。

        每個 route 都採用同一個策略：
        1. 嘗試呼叫真實工具
        2. 如果工具不存在、未完成或報錯，就回傳 mock 資料
        """

        confusion_info = confusion_info or {}

        if route == "clarify":
            return self.mock_clarify_response(confusion_info)

        if route == "clarify_context":
            return self.mock_clarify_context_response(confusion_info)

        if route == "quote_book":
            return self._execute_quote_book(user_id, user_input, mood_intent)

        if route == "quiz_story":
            return self._execute_quiz_story(user_id, user_input, interaction_id)

        if route == "story":
            return self._execute_story(user_id, user_input, interaction_id)

        if route == "preview_purchase":
            return self._execute_preview_purchase(user_id, current_book_id)

        if route == "continue_interaction":
            return self.mock_continue_interaction(interaction_id, user_input)

        if route == "greeting":
            return {
                "type": "greeting",
                "text": "嗨！你可以告訴我最近的心情，或直接說想找哪一類的書，我會幫你推薦。",
                "mock": True,
            }

        return self.mock_fallback_response()

    def _execute_quote_book(self, user_id: str, user_input: str, mood_intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        推薦書與金句流程。

        正式工具如果可用：呼叫 quote_book_tool.recommend()
        失敗時：使用 mock_quote_book_response()
        """

        if self.quote_book_tool is not None:
            try:
                # quote_book_tool.recommend() 目前預期吃 MoodIntentOutput。
                # 但 schema 現在欄位還不完全一致，所以這裡先嘗試直接丟 dict。
                # 如果工具要求 Pydantic model 而失敗，就會自動 fallback mock。
                if hasattr(self.quote_book_tool, "recommend"):
                    result = self.quote_book_tool.recommend(mood_intent)  # type: ignore[arg-type]
                    return self._normalize_tool_result(result, default_type="quote_book", mock=False)
            except Exception as exc:
                logger.warning("quote_book_tool failed, fallback to mock: %s", exc)

        return self.mock_quote_book_response(mood_intent)

    def _execute_quiz_story(self, user_id: str, user_input: str, interaction_id: Optional[str]) -> Dict[str, Any]:
        """
        測驗流程。

        目前 quiz_story_tool.py 是空的，所以大多會跑 mock。
        等 D 組完成後，只要工具提供 run() 或 start()，這裡就可以接上。
        """

        if self.quiz_story_tool is not None:
            try:
                if hasattr(self.quiz_story_tool, "run"):
                    result = self.quiz_story_tool.run(user_id=user_id, user_input=user_input, interaction_id=interaction_id)
                    return self._normalize_tool_result(result, default_type="quiz_story", mock=False)
                if hasattr(self.quiz_story_tool, "start"):
                    result = self.quiz_story_tool.start(user_id=user_id)
                    return self._normalize_tool_result(result, default_type="quiz_story", mock=False)
            except Exception as exc:
                logger.warning("quiz_story_tool failed, fallback to mock: %s", exc)

        return self.mock_quiz_story_response()

    def _execute_story(self, user_id: str, user_input: str, interaction_id: Optional[str]) -> Dict[str, Any]:
        """
        互動故事流程。

        壓縮檔中的 story_service.py 目前是空的，所以這裡先回 mock。
        未來如果 D 組做 story_service，可以在這裡替換成 service 呼叫。
        """
        return self.mock_story_response()

    def _execute_preview_purchase(self, user_id: str, current_book_id: Optional[str]) -> Dict[str, Any]:
        """
        試讀/購買導流流程。

        若 preview_purchase_tool 完成就呼叫工具；否則用 mock。
        """

        if self.preview_purchase_tool is not None:
            try:
                if hasattr(self.preview_purchase_tool, "run"):
                    result = self.preview_purchase_tool.run(user_id=user_id, current_book_id=current_book_id)
                    return self._normalize_tool_result(result, default_type="preview_purchase", mock=False)
            except Exception as exc:
                logger.warning("preview_purchase_tool failed, fallback to mock: %s", exc)

        return self.mock_preview_purchase_response(current_book_id)

    def _normalize_tool_result(self, result: Any, default_type: str, mock: bool) -> Dict[str, Any]:
        """
        把各 tool 回傳結果統一轉成 dict。

        因為工具可能回傳：
        - Pydantic model
        - dict
        - None
        所以這裡統一處理，避免 build_response 爆掉。
        """

        if result is None:
            return {"type": default_type, "text": "工具沒有回傳內容。", "mock": True}

        if hasattr(result, "model_dump"):
            data = result.model_dump()
        elif hasattr(result, "dict"):
            data = result.dict()
        elif isinstance(result, dict):
            data = result
        else:
            data = {"raw_result": str(result)}

        data.setdefault("type", default_type)
        data.setdefault("text", self._default_text_for_type(default_type))
        data["mock"] = mock
        return data

    # ------------------------------------------------------------------
    # 6. Mock responses：工具未完成時使用，之後可逐步刪掉或保留作 fallback
    # ------------------------------------------------------------------

    def mock_quote_book_response(self, mood_intent: Dict[str, Any]) -> Dict[str, Any]:
        mood = mood_intent.get("mood", "neutral")

        if mood in ["低落", "焦慮", "憤怒"]:
            book = {
                "id": "mock_book_001",
                "title": "蛤蟆先生去看心理師",
                "author": "羅伯．狄保德",
                "reason": "適合正在低落、壓力大，想被理解與陪伴的讀者。",
            }
            quote = {
                "id": "mock_quote_001",
                "content": "有時候，理解自己的感受，就是改變的開始。",
                "source": "蛤蟆先生去看心理師",
            }
        else:
            book = {
                "id": "mock_book_002",
                "title": "原子習慣",
                "author": "James Clear",
                "reason": "適合想建立習慣、找回行動感的人。",
            }
            quote = {
                "id": "mock_quote_002",
                "content": "真正重要的不是一次巨大的改變，而是每天一點點的累積。",
                "source": "原子習慣",
            }

        return {
            "type": "quote_book",
            "text": f"我先根據你現在的狀態，推薦《{book['title']}》給你。",
            "book": book,
            "quote": quote,
            "mock": True,
        }

    def mock_quiz_story_response(self) -> Dict[str, Any]:
        return {
            "type": "quiz_story",
            "text": "我們可以先用一個小測驗，找出你現在適合讀哪一類書。",
            "interaction_id": "mock_quiz_001",
            "question": "你最近最想從書裡得到什麼？",
            "options": [
                {"id": "A", "text": "被理解與安慰"},
                {"id": "B", "text": "重新找回動力"},
                {"id": "C", "text": "學習新知識"},
                {"id": "D", "text": "逃離現實，進入故事"},
            ],
            "mock": True,
        }

    def mock_story_response(self) -> Dict[str, Any]:
        return {
            "type": "story",
            "text": "你走進一間只在深夜出現的書店，店員把三本書推到你面前。",
            "interaction_id": "mock_story_001",
            "options": [
                {"id": "A", "text": "拿起看起來很溫柔的書"},
                {"id": "B", "text": "拿起封面最神秘的書"},
                {"id": "C", "text": "直接問店員推薦哪一本"},
            ],
            "mock": True,
        }

    def mock_preview_purchase_response(self, current_book_id: Optional[str]) -> Dict[str, Any]:
        return {
            "type": "preview_purchase",
            "text": "如果你對這本書有興趣，可以先看試讀，也可以前往購買頁面。",
            "book_id": current_book_id or "mock_book_001",
            "actions": [
                {"label": "查看試讀", "action": "preview", "url": "https://example.com/sample"},
                {"label": "前往購買", "action": "purchase", "url": "https://example.com/buy"},
            ],
            "mock": True,
        }

    def mock_continue_interaction(self, interaction_id: Optional[str], user_input: str) -> Dict[str, Any]:
        return {
            "type": "continue_interaction",
            "text": f"我收到你的選擇「{user_input}」了，接下來會根據這個選項繼續推薦。",
            "interaction_id": interaction_id,
            "mock": True,
        }

    def mock_clarify_response(self, confusion_info: Dict[str, Any]) -> Dict[str, Any]:
        matches = confusion_info.get("possible_title_matches", [])

        if matches:
            return {
                "type": "clarify",
                "text": "你說的書名我有點不確定，你是不是想找下面其中一本？",
                "possible_matches": matches,
                "mock": True,
            }

        return {
            "type": "clarify",
            "text": "我還不太確定你想找哪種書。你可以告訴我是想被安慰、找動力、學知識，還是想看故事嗎？",
            "options": [
                {"id": "comfort", "text": "想被安慰"},
                {"id": "motivation", "text": "想找回動力"},
                {"id": "knowledge", "text": "想學新知識"},
                {"id": "story", "text": "想看故事"},
            ],
            "mock": True,
        }

    def mock_clarify_context_response(self, confusion_info: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "clarify_context",
            "text": "你是不是想換一本書，或是想重新開始推薦？",
            "current_book_id": confusion_info.get("current_book_id"),
            "options": [
                {"id": "change_book", "text": "換一本書"},
                {"id": "restart", "text": "重新推薦"},
                {"id": "continue", "text": "繼續剛剛那本"},
            ],
            "mock": True,
        }

    def mock_fallback_response(self) -> Dict[str, Any]:
        return {
            "type": "fallback",
            "text": "我目前可以幫你做書籍推薦、金句推薦、閱讀測驗或互動故事。你可以說：我最近很累，推薦一本書給我。",
            "mock": True,
        }

    # ------------------------------------------------------------------
    # 7. Build Response：統一整理給前端
    # ------------------------------------------------------------------

    def build_response(
        self,
        route: str,
        mood_intent: Dict[str, Any],
        tool_result: Dict[str, Any],
        debug: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        統一前端 response 格式。

        不管後面是推薦書、測驗、故事、購買導流，前端都會收到：
        - text_content：聊天框顯示文字
        - action_type：前端要顯示哪種 UI
        - data_payload：完整資料
        - suggestions：快捷按鈕
        """

        action_type_map = {
            "quote_book": "SHOW_BOOK",
            "quiz_story": "SHOW_QUIZ",
            "story": "SHOW_STORY",
            "preview_purchase": "SHOW_PURCHASE",
            "continue_interaction": "CONTINUE_INTERACTION",
            "clarify": "ASK_CLARIFICATION",
            "clarify_context": "ASK_CLARIFICATION",
            "greeting": "CHAT",
            "fallback": "CHAT",
        }

        return {
            "text_content": tool_result.get("text", ""),
            "action_type": action_type_map.get(route, "CHAT"),
            "data_payload": {
                "route": route,
                "mood_intent": mood_intent,
                "result": tool_result,
            },
            "suggestions": self.build_suggestions(route),
            # debug 對開發很有用；正式上線可以拿掉或只在 dev mode 顯示。
            "debug": debug or {},
        }

    def build_suggestions(self, route: str) -> List[str]:
        """
        依照目前 route 給前端快捷按鈕文字。
        """

        if route == "quote_book":
            return ["我想看更多推薦", "換一本書", "開始測驗", "查看試讀"]

        if route == "quiz_story":
            return ["開始測驗", "直接推薦一本書", "我想看故事"]

        if route == "story":
            return ["繼續故事", "換成測驗", "直接推薦一本書"]

        if route == "preview_purchase":
            return ["查看試讀", "前往購買", "換一本書"]

        if route in ["clarify", "clarify_context"]:
            return ["想被安慰", "想找回動力", "想學新知識", "想看故事"]

        return ["推薦一本書給我", "我想做測驗", "我想玩互動故事"]

    def _default_text_for_type(self, result_type: str) -> str:
        """工具沒有提供 text 時，給一個預設文字。"""
        mapping = {
            "quote_book": "我幫你找到一組書籍與金句推薦。",
            "quiz_story": "我們可以開始一個閱讀測驗。",
            "story": "我們可以開始一段互動故事。",
            "preview_purchase": "這裡是試讀與購買資訊。",
        }
        return mapping.get(result_type, "我已經處理完你的請求。")
