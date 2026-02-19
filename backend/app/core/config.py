import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DEEPSEEK_API_KEY: str
    # Default to 'workspace' folder in the project root if WORKSPACE_ROOT not in ENV
    WORKSPACE_ROOT: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "workspace")
    GMAIL_USER: str = ""
    GMAIL_APP_PASSWORD: str = ""
    
    @property
    def DB_PATH(self): return os.path.join(self.WORKSPACE_ROOT, "memory", "procurement.db")
    @property
    def CHROMA_PATH(self): return os.path.join(self.WORKSPACE_ROOT, "memory", "chroma")
    @property
    def INBOX_DIR(self): return os.path.join(self.WORKSPACE_ROOT, "inbox")
    @property
    def RFQ_DIR(self): return os.path.join(self.WORKSPACE_ROOT, "rfq")
    @property
    def ORDERS_DIR(self): return os.path.join(self.WORKSPACE_ROOT, "orders")
    @property
    def ARCHIVE_DIR(self): return os.path.join(self.WORKSPACE_ROOT, "archive")
    @property
    def OUTPUT_DIR(self): return os.path.join(self.WORKSPACE_ROOT, "output")
    @property
    def MEMORY_DIR(self): return os.path.join(self.WORKSPACE_ROOT, "memory")

    class Config:
        env_file = ".env"

settings = Settings()
