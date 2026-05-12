from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # 1. 資料庫設定
    MONGO_URI="mongodb+srv://sophia20050202_db_user:191516@cluster0.c6ahwlu.mongodb.net/?appName=Cluster0"
    DB_NAME: str = "Cluster0"

    # 2. AI 模型設定
    #GEMINI_API_KEY: str
    #MODEL_NAME: str = " "

    # 3. 系統路徑與其他設定
    #EMBEDDING_MODEL_PATH: str = "sentence-transformers/all-MiniLM-L6-v2"
    #DEBUG: bool = True

    # 讀取 .env 檔案的設定
    model_config = SettingsConfigDict(env_file=".env")

# 實例化成一個可全域呼叫的物件
settings = Settings()