from functools import lru_cache

from pydantic_settings import BaseSettings
from typing import Optional
from urllib.parse import quote_plus

class Settings(BaseSettings):
    server_ip: str = "localhost"
    # Database settings
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "dzy2001818"
    mysql_db: str = "health_agent"
    
    jwt_secret_key: str = "hkasdjhgasdghlkasjhgklasuhowaefabase"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24 * 7  # 7天
    
    @property
    def sqlalchemy_database_uri(self) -> str:
        password = quote_plus(self.mysql_password)
        return (
            f"mysql+pymysql://{self.mysql_user}:{password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}?charset=utf8mb4"
        )
    
    
    # Redis settings
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = "dzy2001818"
    chat_window_rounds: int = 3
    chat_window_ttl_seconds: int = 60 * 60 * 24 * 7  # 7天
    chat_summary_qdrant_collection: str = "chat_summary_memory"

    qdrant_url: str = f"http://{server_ip}:6333"
    
    neo4j_url: str = f"bolt://{server_ip}:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "dzy2001818"
    
     # LLM settings
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_api_key: str = "sk-03ae1e6cb82d4b22baa2b3fad5eec971"
    llm_model: str = "qwen3.5-plus"

    # LVLM settings
    lvlm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    lvlm_api_key: str = "sk-03ae1e6cb82d4b22baa2b3fad5eec971"
    lvlm_model: str = "qwen3.5-plus"

    # Embedding settings
    embedding_base_url: str = "https://api.jina.ai/v1/embeddings"
    embedding_api_key: str = "jina_05b39064ed6c48efa357c997408919fecGVGA_i-00jZLIbx7R8nCNsKUJpo"
    embedding_model: str = "jina-embeddings-v4"

    
    # Application settings
    default_region: str = "CN"
    top_k: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache
def get_settings() -> Settings:
    return Settings()