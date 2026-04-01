from pydantic import BaseModel
from typing import Dict, Optional

class RetrievalResult(BaseModel):
    source_type: str  # "graph" / "rag"
    title: str
    content: str
    score: float
    metadata: Dict