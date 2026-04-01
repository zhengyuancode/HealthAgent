from typing import Any, Dict, List, Optional


class MedicalGraphService:
    def query(
        self,
        query: str,
        entities: Optional[List[str]] = None,
        semantic_type: str = "",
    ) -> Dict[str, Any]:
        raise NotImplementedError


class PolicyRAGService:
    def retrieve(
        self,
        query: str,
        entities: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError