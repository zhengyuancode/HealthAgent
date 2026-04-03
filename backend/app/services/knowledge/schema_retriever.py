from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Dict, List
from dataclasses import field
import hashlib
import pickle
from qdrant_client import models
import torch

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
from app.llm.client import EmbeddingClient
from tqdm import tqdm

@dataclass
class SchemaDoc:
    item_type: str              # entity / relation
    std_name: str               # 图谱里的标准名字
    label: str = ""             # 节点标签，如 Disease / Drug / Symptom
    aliases: List[str] = field(default_factory=list)
    desc: str = ""

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []

    def to_text(self) -> str:
        parts = [f"类型: {self.item_type}", f"标准名: {self.std_name}"]

        if self.label:
            parts.append(f"标签: {self.label}")

        if self.aliases and len(self.aliases) > 0:
            parts.append(f"别名: {'，'.join(self.aliases)}")

        if self.desc:
            parts.append(f"详细介绍: {self.desc}")

        return "\n".join(parts)

    def to_payload(self) -> Dict[str, Any]:
        return {
            "item_type": self.item_type,
            "std_name": self.std_name,
            "label": self.label,
            "aliases": self.aliases,
            "desc": self.desc,
            "semantic_type": self.semantic_type,
        }
        
def unique_keep_order(items):
    seen = set()
    result = []
    for x in items:
        if x not in seen:
            seen.add(x)
            result.append(x)
    return result

class QdrantSchemaRetriever:
    ENTITY_SCORE_THRESHOLD = 0.45
    RELATION_SCORE_THRESHOLD = 0.35
    def __init__(
        self,
        client: QdrantClient,
        embedder: EmbeddingClient,
        collection_name: str = "medical_schema",
        dim: int = 128
    ):
        self.client = client
        self.embedder = embedder
        self.collection_name = collection_name
        self.dim = dim

    def ensure_collection(self, vector_size: int) -> None:
        if self.client.collection_exists(self.collection_name):
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )
    
    def make_id(self, doc: SchemaDoc, k: int) -> str:
        raw = f"{doc.label}::{doc.std_name}::{k}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()
    
    def rebuild_index(self, docs: List[SchemaDoc], recreate: bool = False) -> None:
        if not docs:
            raise ValueError("docs 不能为空")

        if recreate and self.client.collection_exists(self.collection_name):
            self.client.delete_collection(self.collection_name)
            
        self.ensure_collection(self.dim)
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="doc_key",
            field_schema=models.PayloadSchemaType.KEYWORD,
            wait=True,
        )

        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="seq_num",
            field_schema=models.PayloadSchemaType.INTEGER,
            wait=True,
        )
        
        
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        vector_path = os.path.join(BASE_DIR,"..","..","graph", "entity_vectors.pkl")
        with open(vector_path, 'rb') as f:
            entity_vectors = pickle.load(f)
        
        for doc, vector in tqdm(zip(docs, entity_vectors), desc="Indexing schema docs"):
            points = []
            for k in range(len(vector)):
                points.append({
                    "id": self.make_id(doc, k),
                    "vector": vector[k].detach().cpu().tolist(),
                    "payload": {
                        "doc_key": f"{doc.label}_{doc.std_name}",
                        "seq_num": k
                    }
                })
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )
        # batch_size = 10
        # upsert_batch_size = 500
        # for i in tqdm(range(0, len(docs), batch_size), desc="Indexing schema docs", unit="batch"):
        #     try:
        #         batch_docs = docs[i:i + batch_size]
        #         batch_texts = [doc.to_text() for doc in batch_docs]

        #         batch_vectors = self.embedder.embed_content(
        #             batch_texts,
        #             task="retrieval.passage"
        #         )
                
        #         points = []
        #         for doc, vector in tqdm(zip(batch_docs, batch_vectors), desc="Processing batch"):
        #             for k in range(len(vector["embeddings"])):
        #                 points.append({
        #                     "id": self.make_id(doc, k),
        #                     "vector": vector["embeddings"][k],
        #                     "payload": {
        #                         "doc_key": f"{doc.label}::{doc.std_name}",
        #                         "seq_num": k
        #                     }
        #                 })

        #         for start in tqdm(range(0, len(points), upsert_batch_size), desc="Upserting points"):
        #             sub_points = points[start:start + upsert_batch_size]
        #             self.client.upsert(
        #                 collection_name=self.collection_name,
        #                 points=sub_points,
        #             )
        #     except Exception as e:
        #         print(f"batch {i} failed: {e}")
        #         raise

        
        

        

    def _search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        query_vector = self.embedder.embed_content(
                    [query],
                    task="retrieval.query"
                )

       
        resp = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector[0]["embedding"],
            # query_filter=qfilter,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )

        hits = getattr(resp, "points", resp)

        results: List[Dict[str, Any]] = []
        for hit in hits:
            payload = hit.payload or {}
            results.append(
                {
                    "score": hit.score,
                    "std_name": payload.get("std_name", ""),
                    "aliases": payload.get("aliases", []),
                    "desc": payload.get("desc", ""),
                    "semantic_type": payload.get("semantic_type", ""),
                    "item_type": payload.get("item_type", ""),
                }
            )
        return results

    def retrieve_entities(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        return self._search(query=query, item_type="entity", top_k=top_k)

    def retrieve_relations(self, query: str, top_k: int = 1) -> List[Dict[str, Any]]:
        return self._search(query=query, item_type="relation", top_k=top_k)

    def ground(
        self,
        query: str,
        entity_top_k: int = 5,
        relation_top_k: int = 3,
    ) -> Dict[str, Any]:
        entity_hits = self.retrieve_entities(query, top_k=entity_top_k)
        relation_hits = self.retrieve_relations(query, top_k=relation_top_k)

        entity_hits = [
            x for x in entity_hits
            if x["score"] >= self.ENTITY_SCORE_THRESHOLD
        ]
        relation_hits = [
            x for x in relation_hits
            if x["score"] >= self.RELATION_SCORE_THRESHOLD
        ]

        normalized_entities = unique_keep_order(
            [x["std_name"] for x in entity_hits]
        )

        semantic_type = ""
        if relation_hits:
            semantic_type = relation_hits[0].get("semantic_type", "") or ""

        return {
            "entity_hits": entity_hits,
            "relation_hits": relation_hits,
            "normalized_entities": normalized_entities,
            "semantic_type": semantic_type,
        }