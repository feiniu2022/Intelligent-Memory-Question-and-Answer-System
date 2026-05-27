"""项目配置文件 - 使用 pydantic-settings 管理"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings

# 兼容旧代码：项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # ========== LLM ==========
    chat_model: str = "deepseek-v4-pro"
    chat_base_url: str = "https://opencode.ai/zen/go/v1"
    chat_api_key: str = ""

    # ========== Embedding ==========
    embedding_model: str = "qwen3-embedding:4b"
    ollama_base_url: str = "http://localhost:11434"

    # ========== 存储路径 ==========
    base_dir: Path = Path(BASE_DIR)
    memory_db_dir: str = "data/memory_db"
    knowledge_db_dir: str = "data/knowledge_db"
    txt_data_dir: str = "data/txt_files"
    upload_dir: str = "uploads"

    # ========== 检索配置 ==========
    hybrid_search_k: int = 5
    hybrid_search_alpha: float = 0.5

    # ========== RAG ==========
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 50
    rag_top_k: int = 5
    rag_hyde_enabled: bool = True

    # ========== Agent ==========
    max_messages: int = 30
    summary_threshold: int = 20

    # ========== JWT ==========
    jwt_secret: str = "change-this-secret-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # ========== 数据库 ==========
    db_path: str = "data/app.db"

    # ========== 服务 ==========
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    # ========== 路径解析 ==========
    @property
    def resolved_memory_db_dir(self) -> Path:
        p = Path(self.memory_db_dir)
        if not p.is_absolute():
            p = self.base_dir / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def resolved_knowledge_db_dir(self) -> Path:
        p = Path(self.knowledge_db_dir)
        if not p.is_absolute():
            p = self.base_dir / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def resolved_txt_data_dir(self) -> Path:
        p = Path(self.txt_data_dir)
        if not p.is_absolute():
            p = self.base_dir / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def resolved_db_path(self) -> Path:
        p = Path(self.db_path)
        if not p.is_absolute():
            p = self.base_dir / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def resolved_checkpoint_db_path(self) -> Path:
        p = self.base_dir / "data" / "checkpoints.db"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def resolved_upload_dir(self) -> Path:
        p = Path(self.upload_dir)
        if not p.is_absolute():
            p = self.base_dir / p
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()

# 兼容旧代码：全局变量
OLLAMA_BASE_URL = settings.ollama_base_url
EMBEDDING_MODEL = settings.embedding_model
CHAT_MODEL = settings.chat_model
CHAT_BASE_URL = settings.chat_base_url
CHAT_API_KEY = settings.chat_api_key
MEMORY_DB_DIR = str(settings.resolved_memory_db_dir)
KNOWLEDGE_DB_DIR = str(settings.resolved_knowledge_db_dir)
TXT_DATA_DIR = str(settings.resolved_txt_data_dir)
HYBRID_SEARCH_K = settings.hybrid_search_k
HYBRID_SEARCH_ALPHA = settings.hybrid_search_alpha
MAX_MESSAGES = settings.max_messages