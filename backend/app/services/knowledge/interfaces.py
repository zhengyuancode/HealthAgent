from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.services.knowledge.schema_retriever import QdrantSchemaRetriever


class MedicalGraphService(ABC):
    @abstractmethod
    def query(
        self,
        query: str,
        retriever: QdrantSchemaRetriever,
        entities: Optional[List[str]] = None,
        semantic_type: str = "",
        topk: int = 5,
        topn: int = 5
    ) -> Dict[str, Any]:
        raise NotImplementedError
        

class PolicyRAGService(ABC):
    @abstractmethod
    def retrieve(
        self,
        query: str,
        entities: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError