import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# 定義專案根目錄路徑
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """
    系統全域設定類別
    自動從專案根目錄的 .env 檔案中讀取環境變數
    """
    
    # 1. API Key (設為 Optional，沒填時預設為 None)
    API_KEY: Optional[str] = None
    
    # 2. 模型名稱與參數
    #LLM_MODEL_NAME: str = "gemini-1.5-flash"
    #SYSTEM_TEMPERATURE: float = 0.3
    
    # 3. 資料庫設定 
    MONGO_URI: str
    MONGO_DB_NAME: str = "book_agent_db" 
    # 使用 Pydantic Settings 讀取 .env 的核心設定
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore" # 如果 .env 有多寫其他東西，自動忽略不報錯
    )

# 實例化全域設定物件，其他檔案直接 import 這個 settings 即可
settings = Settings()
