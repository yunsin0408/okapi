"""後端核心大腦與記憶一體化測試腳本 (B角色架構師專用 - 雙相導航版)"""

import sys
import os

# 🚀 1. 精準抓取路徑
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))      # backend 資料夾
PARENT_DIR = os.path.dirname(CURRENT_DIR)                     # okapi-main 最外層資料夾

# 🚀 2. 強制硬塞環境變數，直接打爆 Pydantic Missing Error
os.environ["MONGO_URI"] = "mongodb+srv://sophia20050202_db_user:191516@cluster0.c6ahwlu.mongodb.net/?retryWrites=true&w=majority"
os.environ["MONGO_DB_NAME"] = "book_agent_db"
os.environ["HF_TOKEN"] = "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"

# 🚀 3. 【核心修正】：同時把內層和外層塞進 Python 地圖！
# 這樣一來，不管是寫 from core 還是 from backend.core，Python 通通都認得！
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

# 讓當前工作目錄錨定在 backend
os.chdir(CURRENT_DIR)

# ==============================================================================
# 👆 雙向導航已布線完成，👇 接下來工具引入絕對不會再噴 No module named 'backend' 了！
# ==============================================================================

from agents.book_agent import BookAgent
from core.memory import MemoryManager

def run_integration_test():
    # ... 下面所有對話與測試流程完全保持不變 ...
    # ... 下面所有對話與測試流程完全保持不變 ...
    print("=" * 50)
    print("🎯  正在啟動 Book Agent 與記憶中樞整合測試...")
    print("=" * 50)

    # 1. 初始化總控台與記憶管理器
    # (這裡先不傳 db_client，讓 memory 跑本地短期快取模式，排除資料庫干擾)
    memory_manager = MemoryManager(db_client=None)
    agent = BookAgent()

    # 定義一個假想的測試客人
    test_user_id = "郭孟綺"

    # 2. 模擬連續對話測試流
    test_prompts = [
        "嗨，你好！",                                      # 測試點 1：打招呼路由 (Greeting)
        "我今天期末考快被當了，心情好低落、壓力好大...",        # 測試點 2：情緒偵測與書本金句推薦 (Quote Book)
        "我想做心理測驗看看我適合哪本書",                     # 測試點 3：測驗路由觸發 (Quiz)
        "這本書哪裡買？有試讀連結嗎？"                        # 測試點 4：導購路由觸發 (Purchase)
    ]

    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n[第 {i} 輪對話] 👤 客人說: '{prompt}'")
        
        # 🌟 模擬後端收案流程 1：大腦一收到訊息，記憶管理器立刻寫入本地短期快取
        # (這裡模擬 UserRequest 傳入文字)
        from models.schema import UserRequest
        import time
        req = UserRequest(user_id=test_user_id, message=prompt, timestamp=time.time())
        memory_manager.update_user_message(test_user_id, req)

        # 🌟 模擬後端收案流程 2：正式呼叫 BookAgent 的大腦總控台
        response = agent.run(
            user_id=test_user_id,
            user_input=prompt,
            interaction_id=None, # 這裡可模擬傳入測驗題號
            current_book_id="mock_book_001" if i == 4 else None # 第四輪時帶入目前書本ID
        )

        # 🌟 模擬後端收案流程 3：大腦回話後，記憶管理器記下 AI 的回話
        memory_manager.update_agent_response(test_user_id, response["text_content"])

        # 3. 列印大腦打包給前端的精美結果
        print(f"🤖 Agent 回應文字: {response['text_content']}")
        print(f"🎬 前端 UI 動態行為 (action_type): {response['action_type']}")
        print(f"🗂️ 核心數據載荷 (data_payload): {response['data_payload']}")
        print(f"🔘 下方快捷按鈕 (suggestions): {response['suggestions']}")
        
        # 4. 關鍵看點：偷看妳的記憶便利貼有沒有在運作！
        current_memory = memory_manager.get_user_memory(test_user_id)
        print(f"🧠 [總管便利貼現況] 當前聊天紀錄行數: {len(current_memory.chat_history)} 句")
        print("-" * 50)

if __name__ == "__main__":
    run_integration_test()
