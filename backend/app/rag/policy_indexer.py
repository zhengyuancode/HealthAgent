import json
import re
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
from docx import Document
from qdrant_client import QdrantClient, models
from tqdm import tqdm
from app.llm.client import EmbeddingClient
from app.core.config import Settings


@dataclass
class PolicyChunk:
    chunk_id: str
    doc_name: str
    chunk_index: int
    text: str
    source_path: str



def extract_multivector(embedding_model, text: str, prompt_name: str) -> np.ndarray:
    result = embedding_model.embed_content(
                    [{"text": text}],
                    task="retrieval.passage"
                )

    vectors = result[0]["embeddings"]
    vectors = np.asarray(vectors, dtype=np.float32)
    return vectors


class PolicyIndexer:
    def __init__(
        self,
        qdrant_client: QdrantClient,
        embedding_model,
        collection_name: str = "policy",
        chunk_store_path: str = "data/policy_chunk_store.json",
        batch_size: int = 2048,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
    ):
        self.client = qdrant_client
        self.embedding_model = embedding_model
        self.collection_name = collection_name
        self.chunk_store_path = Path(chunk_store_path)
        self.batch_size = batch_size
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def build_index(self, policy_dir: str) -> Dict[str, Any]:
        policy_dir = Path(policy_dir)
        if not policy_dir.exists():
            raise FileNotFoundError(f"policy_dir not found: {policy_dir}")

        all_chunks: List[PolicyChunk] = []

        for file_path in sorted(policy_dir.iterdir()):
            if not file_path.is_file():
                continue

            suffix = file_path.suffix.lower()
            if suffix not in {".txt", ".docx", ".wps"}:
                continue

            text = self._read_file(file_path)
            if not text.strip():
                continue

            chunks = self._chunk_text(text)
            for idx, chunk_text in enumerate(chunks):
                chunk_id = f"{file_path.stem}__chunk_{idx}"
                all_chunks.append(
                    PolicyChunk(
                        chunk_id=chunk_id,
                        doc_name=file_path.name,
                        chunk_index=idx,
                        text=chunk_text,
                        source_path=str(file_path),
                    )
                )

        if not all_chunks:
            raise ValueError("No valid policy chunks found.")

        # 先拿第一个 chunk 推出向量维度
        first_vectors = extract_multivector(
            self.embedding_model,
            all_chunks[0].text,
            prompt_name="passage",
        )
        vector_size = first_vectors.shape[1]

        self._recreate_collection(vector_size)

        chunk_store: Dict[str, Dict[str, Any]] = {}
        points_buffer: List[models.PointStruct] = []

        for i, chunk in tqdm(enumerate(all_chunks), total=len(all_chunks), desc="Indexing policy chunks"):
            if i == 0:
                vectors = first_vectors
            else:
                vectors = extract_multivector(
                    self.embedding_model,
                    chunk.text,
                    prompt_name="passage",
                )

            chunk_store[chunk.chunk_id] = asdict(chunk)

            for seq_num, vec in enumerate(vectors):
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{chunk.chunk_id}_{seq_num}"))
                points_buffer.append(
                    models.PointStruct(
                        id=point_id,
                        vector=vec.tolist(),
                        payload={
                            "chunk_id": chunk.chunk_id,
                            "doc_name": chunk.doc_name,
                            "chunk_index": chunk.chunk_index,
                            "seq_num": seq_num,
                        },
                    )
                )

            if len(points_buffer) >= self.batch_size:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points_buffer,
                )
                points_buffer = []

        if points_buffer:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points_buffer,
            )

        self.chunk_store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.chunk_store_path, "w", encoding="utf-8") as f:
            json.dump(chunk_store, f, ensure_ascii=False, indent=2)

        return {
            "collection_name": self.collection_name,
            "doc_count": len({c.doc_name for c in all_chunks}),
            "chunk_count": len(all_chunks),
            "chunk_store_path": str(self.chunk_store_path),
        }

    def _recreate_collection(self, vector_size: int) -> None:
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            ),
        )

    def _read_file(self, file_path: Path) -> str:
        suffix = file_path.suffix.lower()

        if suffix == ".txt":
            return self._read_txt(file_path)

        if suffix == ".docx":
            doc = Document(str(file_path))
            parts = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
            return self._clean_text("\n".join(parts))

        if suffix == ".wps":
            print(f"[WARN] Skip unsupported .wps file for now: {file_path}")
            return ""

        return ""

    def _read_txt(self, file_path: Path) -> str:
        for encoding in ("utf-8", "utf-8-sig", "gb18030", "gbk"):
            try:
                return self._clean_text(file_path.read_text(encoding=encoding))
            except Exception:
                continue
        raise UnicodeDecodeError(
            "unknown", b"", 0, 1, f"Cannot decode txt file: {file_path}"
        )

    def _clean_text(self, text: str) -> str:
        text = text.replace("\u3000", " ")
        text = text.replace("\xa0", " ")
        text = re.sub(r"\r\n?", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _chunk_text(self, text: str) -> List[str]:
        """
        先按自然段切，再合并到 chunk_size 左右；
        段落特别长时，再做滑窗切分。
        """
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if not paragraphs:
            return []

        chunks: List[str] = []
        current = ""

        for para in paragraphs:
            if len(para) > self.chunk_size:
                if current:
                    chunks.append(current.strip())
                    current = ""

                long_chunks = self._split_long_text(para)
                chunks.extend(long_chunks)
                continue

            candidate = para if not current else f"{current}\n\n{para}"
            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                chunks.append(current.strip())
                current = para

        if current:
            chunks.append(current.strip())

        return chunks

    def _split_long_text(self, text: str) -> List[str]:
        chunks = []
        start = 0
        step = self.chunk_size - self.chunk_overlap

        while start < len(text):
            end = start + self.chunk_size
            piece = text[start:end].strip()
            if piece:
                chunks.append(piece)
            start += step

        return chunks

def main():
    settings = Settings()
    embedding_model = EmbeddingClient(settings)
    qdrant_client = QdrantClient(
                host=settings.server_ip,
                port=6333,
                timeout=120.0,
            )

    indexer = PolicyIndexer(
        qdrant_client=qdrant_client,
        embedding_model=embedding_model,
        collection_name="policy",
        chunk_store_path="data/policy_chunk_store.json",
        batch_size=2048,
        chunk_size=800,
        chunk_overlap=120,
    )

    result = indexer.build_index("D:\\codeworkspace\\python\\HealthAgent\\backend\\app\\seed_data\\policy")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
if __name__ == "__main__":
    main()