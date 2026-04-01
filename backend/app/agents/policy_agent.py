import json
from typing import Any, Dict, List

from app.schemas.agent import RagExecutionOutput, TaskPlan
from app.services.knowledge.interfaces import PolicyRAGService


class PolicyRAGAgent:
    name = "policy_rag_agent"

    def __init__(self, llm_client, policy_rag_service: PolicyRAGService):
        self.policy_rag_service = policy_rag_service
        self.llm_client = llm_client

    def run(
        self,
        task: TaskPlan
    ) -> RagExecutionOutput:
        try:
            rag_docs = self.policy_rag_service.retrieve(
                query=task.question,
                entities=task.entities,
                top_k=5,
            )

            summary = self._summarize(task, rag_docs)

            return RagExecutionOutput(
                task=task,
                summary=summary,
                evidence=[{"source": "policy_rag", "content": doc} for doc in rag_docs],
                status="success"
            )
        except Exception as e:
            return RagExecutionOutput(
                task=task,
                summary=f"RAG检索失败: {e}",
                evidence=[],
                status="failed"
            )

    def _summarize(self, task: TaskPlan, rag_docs: List[Dict[str, Any]]) -> str:
        if self.llm_client is None:
            return f"已完成政策检索：{task.question}"

        system_prompt = """
你是医疗问答系统中的 PolicyRAG Agent。
请基于检索到的政策文本进行回复。
"""
        user_prompt = f"""
子问题：{task.question}

政策检索结果：
{json.dumps(rag_docs, ensure_ascii=False, indent=2)}
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.llm_client.chat(messages=messages, thinking=False).strip()