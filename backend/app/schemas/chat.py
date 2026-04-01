from pydantic import BaseModel
from typing import List, Optional, Dict

class ChatRequest(BaseModel):
    user_query: str
    session_id: Optional[str] = None
    region: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    risk_notice: Optional[str] = None
    sources: List[Dict]
    graph_evidence: List[Dict]
    rag_evidence: List[Dict]
    route_info: Dict