from typing import Any, Dict, List, Optional
from app.services.knowledge.schema_retriever import QdrantSchemaRetriever


class MedicalGraphService:
    def query(
        self,
        query: str,
        retriever: QdrantSchemaRetriever,
        entities: Optional[List[str]] = None,
        semantic_type: str = "",
        topk: int = 5,
        topn: int = 5
    ) -> Dict[str, Any]:
        emb_entities = []
        docs = retriever.search(query, topk, topn)
        for doc in docs:
            emb_entities.append({
                "label": doc["doc_key"].split('_', 1)[0],
                "name": doc["doc_key"].split('_', 1)[1]
            })
        

class PolicyRAGService:
    def retrieve(
        self,
        query: str,
        entities: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError