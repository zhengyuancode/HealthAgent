from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    server_ip: str = "192.168.0.102"
    # Database settings
    mysql_url: str = "mysql+pymysql://dzy:dzy2001818@localhost:3306/health_db"
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