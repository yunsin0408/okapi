from typing import Optional, Dict, Any, List
from models.schema import MemoryState, UserRequest, MoodIntentOutput
from core.config import settings

class MemoryManager:
    """
    系統記憶中樞 (Memory Manager) - Lean Data 高效能業界版
    
    【核心架構】：
    1. chat_history (對話紀錄)：僅留存在本地 Application Layer 快取中，不落資料庫，保護隱私並優化傳輸效能。
    2. 重要特徵 (偏好、書單、測驗進度、分數)：實時同步至 MongoDB Atlas，確保跨裝置/重新登入時核心功能不中斷。
    """
    
    def __init__(self, db_client: Optional[Any] = None):
        """
        初始化記憶管理器。
        :param db_client: MongoDB client 物件。
        """
        self.db_client = db_client
        
        # 本地記憶體快取 (短期快取桌面)，結構為 { user_id: MemoryState_dict }
        self._local_storage: Dict[str, Dict[str, Any]] = {}
        
        if self.db_client:
            self.db = self.db_client[settings.MONGO_DB_NAME]
            self.collection = self.db["user_memories"]

    def _load_from_db(self, user_id: str) -> Optional[Dict[str, Any]]:
        """內部方法：從 MongoDB 撈取使用者的『黃金重要特徵』"""
        if self.db_client:
            try:
                return self.collection.find_one({"user_id": user_id})
            except Exception as e:
                print(f"[Memory Warning] 無法從 MongoDB 讀取特徵: {e}")
        return None

    def _save_to_db(self, user_id: str, memory_dict: Dict[str, Any]):
        """內部方法：將重要特徵同步回 MongoDB（過濾掉對話歷史，落實 Lean Data）"""
        if self.db_client:
            try:
                # 備份一份資料，準備送往雲端
                cloud_data = memory_dict.copy()
                
                # 【架構師核心優化】：強行清空要送往雲端的對話紀錄，不讓廢話佔用雲端空間
                cloud_data["chat_history"] = []
                
                # 使用 upsert=True 更新或新增重要特徵卡片
                self.collection.update_one(
                    {"user_id": user_id},
                    {"$set": cloud_data},
                    upsert=True
                )
            except Exception as e:
                print(f"[Memory Error] 重要特徵同步至 MongoDB 失敗: {e}")

    def get_user_memory(self, user_id: str) -> MemoryState:
        """
        [讀取記憶]
        每一輪對話開始時呼叫。會融合『本地快取的最新對話』與『資料庫的長期偏好』。
        """
        # 1. 如果本地快取桌面上已經有這個人，直接回傳（包含他最新的對話與特徵）
        if user_id in self._local_storage:
            return MemoryState(**self._local_storage[user_id])
        
        # 2. 如果本地沒有（使用者重新登入/新開網頁），去雲端撈取他的黃金特徵
        db_record = self._load_from_db(user_id)
        if db_record:
            db_record.pop("_id", None) # 移除 MongoDB 自動生成的識別碼
            # 此時撈回來的 chat_history 必然是空陣列 []
            self._local_storage[user_id] = db_record
            return MemoryState(**db_record)
        
        # 3. 兩邊都沒有，代表是全新的使用者
        new_memory = MemoryState(
            user_id=user_id,
            chat_history=[],
            detected_preferences=[],
            recommended_book_ids=[],
            quiz_scores={},
            current_scene_id=None
        )
        
        self._local_storage[user_id] = new_memory.model_dump()
        self._save_to_db(user_id, self._local_storage[user_id])
        return new_memory

    def update_user_message(self, user_id: str, user_request: UserRequest):
        """
        [記憶更新 - 步驟 1]
        使用者講話時，只記在本地短期快取，絕對不驚動雲端資料庫。
        """
        memory = self.get_user_memory(user_id)
        
        # 僅在本地附加對話
        memory.chat_history.append({"role": "user", "content": user_request.message})
        
        # 滾動裁剪防 Token 爆炸
        if len(memory.chat_history) > settings.MAX_CHAT_HISTORY_LENGTH:
            memory.chat_history = memory.chat_history[-settings.MAX_CHAT_HISTORY_LENGTH:]
            
        # 更新本地桌面，不呼叫 _save_to_db
        self._local_storage[user_id] = memory.model_dump()

    def update_ai_analysis(self, user_id: str, analysis_output: MoodIntentOutput):
        """
        [記憶更新 - 步驟 2]
        C 組分析出偏好標籤 -> 納入重要特徵 -> 實時同步到雲端 MongoDB！
        """
        memory = self.get_user_memory(user_id)
        
        current_mood = analysis_output.mood
        if current_mood and current_mood not in memory.detected_preferences:
            memory.detected_preferences.append(current_mood)
            
        if len(memory.detected_preferences) > settings.MAX_PREFERENCE_TAGS:
            memory.detected_preferences.pop(0)
            
        self._local_storage[user_id] = memory.model_dump()
        self._save_to_db(user_id, self._local_storage[user_id]) # 觸發雲端同步

    def add_recommendation_history(self, user_id: str, book_id: str):
        """
        [記憶更新 - 步驟 3]
        成功推薦了書 -> 納入重要特徵（黑名單） -> 實時同步到雲端 MongoDB！
        """
        memory = self.get_user_memory(user_id)
        
        if book_id not in memory.recommended_book_ids:
            memory.recommended_book_ids.append(book_id)
            
        self._local_storage[user_id] = memory.model_dump()
        self._save_to_db(user_id, self._local_storage[user_id]) # 觸發雲端同步

    def add_quote_recommendation_history(self, user_id: str, quote_id: str):
        """
        [記憶更新 - 步驟 3-2]
        當系統（C 組工具）成功秀出某個金句時呼叫。
        將該金句的身分證字號 (quote_id) 鎖進黑名單，防止下一輪重複推薦！
        """
        # 1. 請總管把客人的紀錄卡片翻開
        memory = self.get_user_memory(user_id)
        
        # 2. 檢查卡片上新加的這格 recommended_quote_ids，如果這金句沒出現過，就寫進去
        if quote_id not in memory.recommended_quote_ids:
            memory.recommended_quote_ids.append(quote_id)
            
        # 3. 更新總管腰包裡的本地便利貼
        self._local_storage[user_id] = memory.model_dump()
        
        # 4. 小跑步到後台，把包含新金句 ID 的卡片鎖進雲端保險箱！
        self._save_to_db(user_id, self._local_storage[user_id])

    def update_interaction_progress(self, user_id: str, incoming_scores: Dict[str, int], next_scene_id: Optional[str]):
        """
        [記憶更新 - 步驟 4]
        測驗分數與劇情進度更新 -> 納入重要特徵 -> 實時同步到雲端 MongoDB！
        """
        memory = self.get_user_memory(user_id)
        
        for character_key, score_to_add in incoming_scores.items():
            memory.quiz_scores[character_key] = memory.quiz_scores.get(character_key, 0) + score_to_add
            
        memory.current_scene_id = next_scene_id
        
        self._local_storage[user_id] = memory.model_dump()
        self._save_to_db(user_id, self._local_storage[user_id]) # 觸發雲端同步

    def update_agent_response(self, user_id: str, agent_text: str):
        """
        [記憶更新 - 步驟 5]
        AI 回話時，只記在本地短期快取，保持對話連貫，不驚動雲端。
        """
        memory = self.get_user_memory(user_id)
        
        # 僅在本地附加助理對話
        memory.chat_history.append({"role": "assistant", "content": agent_text})
        
        self._local_storage[user_id] = memory.model_dump()

    def clear_quiz_and_story_state(self, user_id: str):
        """
        [清空互動狀態]
        測驗或劇情結束，分數進度重設 -> 重要特徵變更 -> 實時同步到雲端 MongoDB！
        """
        memory = self.get_user_memory(user_id)
        memory.current_scene_id = None
        memory.quiz_scores = {}
        
        self._local_storage[user_id] = memory.model_dump()
        self._save_to_db(user_id, self._local_storage[user_id]) # 觸發雲端同步
