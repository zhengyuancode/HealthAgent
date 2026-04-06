from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import numpy as np
import os
import json

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.core.config import Settings
from app.services.knowledge.interfaces import PolicyRAGService


class LocalPolicyRAGService(PolicyRAGService):
    """
    基于 Qdrant 的本地政策 RAG 检索服务：
    - 第一阶段：按 query 的每个 token 向量召回候选 chunk
    - 第二阶段：对候选 chunk 做 late interaction / MaxSim 重排
    """

    def __init__(self, settings: Settings, embedder=None, collection_name: str = "policy"):
        self.settings = settings
        self.collection_name = collection_name

        if embedder is None:
            raise ValueError("LocalPolicyRAGService 初始化失败：embedder 不能为空")
        self.embedder = embedder

        self.client = QdrantClient(
            url=settings.qdrant_url,
            api_key=getattr(settings, "qdrant_api_key", None),
            prefer_grpc=getattr(settings, "qdrant_prefer_grpc", False),
            timeout=getattr(settings, "qdrant_timeout", 30.0),
        )

    def retrieve(
        self,
        query: str,
        entities: Optional[List[str]] = None,
        top_k: int = 5,
        top_n: int = 5
    ) -> List[Dict[str, Any]]:


        query_embedding_result = self.embedder.embed_content(
            [query],
            task="retrieval.query",
        )

        if not query_embedding_result:
            return []

        query_vectors = query_embedding_result[0].get("embeddings", [])
        if not query_vectors:
            return []

        candidate_chunk_id = self._recall_candidate_chunk_id(
            query_vectors=query_vectors,
            top_n=top_n,
        )

        if not candidate_chunk_id:
            return []

        candidate_docs: List[Dict[str, Any]] = []

        for chunk_id in candidate_chunk_id:
            points = self._load_doc_points(chunk_id)
            if not points:
                continue

            doc_vectors = []
            payload_example: Dict[str, Any] = {}
            seq_pairs = []

            for p in points:
                payload = getattr(p, "payload", None) or {}
                if not payload_example:
                    payload_example = payload

                vector = self._extract_vector(p)
                if vector is None:
                    continue

                doc_vectors.append(vector)


            score = self.late_sim_score(query_vectors, doc_vectors)

            candidate_docs.append(
                {
                    "score": score,
                    "content": self._pick_content(payload_example)
                }
            )

        candidate_docs.sort(key=lambda x: x["score"], reverse=True)
        return candidate_docs[:top_k]

    def late_sim_score(self, query_vectors, doc_vectors) -> float:
        """
        MaxSim / Late Interaction:
        score(Q, D) = sum_q max_d sim(q, d)
        这里用点积；如果你的向量事先做过归一化，那么它就等价于 cosine 相似度。
        """
        query_vectors = np.asarray(query_vectors, dtype=np.float32)  # [Q, D]
        doc_vectors = np.asarray(doc_vectors, dtype=np.float32)      # [T, D]

        if query_vectors.size == 0 or doc_vectors.size == 0:
            return 0.0

        sim_matrix = query_vectors @ doc_vectors.T  # [Q, T]
        return float(np.max(sim_matrix, axis=1).sum())

    def _build_query_text(self, query: str, entities: Optional[List[str]]) -> str:
        """
        将 query 和实体做一个轻量融合。
        实体不是必须，但通常能增强政策检索的召回。
        """
        entities = [e.strip() for e in (entities or []) if e and e.strip()]
        if not entities:
            return query.strip()

        # 简单有效，不搞太复杂
        extra = " ".join(dict.fromkeys(entities))
        return f"{query.strip()} {extra}".strip()

    def _recall_candidate_chunk_id(
        self,
        query_vectors: List[List[float]],
        top_n: int,
    ) -> List[str]:
        candidate_chunk_id: List[str] = []

        for qv in query_vectors:
            resp = self.client.query_points(
                collection_name=self.collection_name,
                query=qv,
                limit=top_n,
                with_payload=True,
                with_vectors=False,
            )

            hits = getattr(resp, "points", resp)

            for hit in hits:
                payload = getattr(hit, "payload", None) or {}
                chunk_id = payload.get("chunk_id", "")
                if not chunk_id:
                    continue
                if chunk_id in candidate_chunk_id:
                    continue

                candidate_chunk_id.append(chunk_id)

        return candidate_chunk_id

    def _load_doc_points(self, chunk_id: str) -> List[Any]:
        scroll_filter = Filter(
            must=[
                FieldCondition(
                    key="chunk_id",
                    match=MatchValue(value=chunk_id)
                )
            ]
        )

        all_points = []
        offset = None

        while True:
            points, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=scroll_filter,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=True,
            )

            if not points:
                break

            all_points.extend(points)

            if next_offset is None:
                break

            offset = next_offset

        return all_points

    def _extract_vector(self, point) -> Optional[List[float]]:
        """
        兼容不同 qdrant-client 返回结构：
        - point.vector
        - point.vectors
        - named vector dict
        """
        vector = None

        if hasattr(point, "vector") and point.vector is not None:
            vector = point.vector
        elif hasattr(point, "vectors") and point.vectors is not None:
            vector = point.vectors

        if vector is None:
            return None

        # named vector 的情况
        if isinstance(vector, dict):
            if self.vector_name and self.vector_name in vector:
                vector = vector[self.vector_name]
            else:
                # 没配置 vector_name 时，默认取第一个
                vector = next(iter(vector.values()), None)

        if vector is None:
            return None

        return list(vector)

    def _pick_content(self, payload: Dict[str, Any]) -> str:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        chunk_path = os.path.join(BASE_DIR,"..", "..","rag","data","policy_chunk_store.json") 
        chunk_id = payload.get("chunk_id")
        with open(chunk_path, "r", encoding="utf-8") as f:
            # 加载JSON数据为Python字典/列表
            chunk_data = json.load(f)
        return chunk_data[chunk_id]["text"]
        