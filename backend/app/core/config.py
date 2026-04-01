from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    server_ip: str = "192.168.0.102"
    # Database settings
    mysql_url: str = "mysql+pymysql://dzy:dzy2001818@localhost:3306/health_db"
    qdrant_url: str = f"http://{server_ip}:6333"
    neo4j_url: str = f"bolt://{server_ip}:7687"
    
     # LLM settings
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    # LVLM settings
    lvlm_base_url: str = ""
    lvlm_api_key: str = ""
    lvlm_model: str = ""

    # Embedding settings
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = ""

    
    # Application settings
    default_region: str = "CN"
    top_k: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = True