from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    session_id: int = Field(..., description="会话ID")
    query: str = Field(..., min_length=1, description="用户问题")
    
    


