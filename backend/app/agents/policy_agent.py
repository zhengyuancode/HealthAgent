import json
import asyncio
from typing import Any, Dict, List, AsyncGenerator

from app.schemas.agent import RagExecutionOutput, TaskPlan
from app.services.knowledge.interfaces import PolicyRAGService


class PolicyRAGAgent:
    name = "policy_rag_agent"

    def __init__(self, llm_client, policy_rag_service: PolicyRAGService):
        self.policy_rag_service = policy_rag_service
        self.llm_client = llm_client

    def run(self, task: TaskPlan) -> RagExecutionOutput:
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

    async def stream_run(self, task: TaskPlan) -> AsyncGenerator[Dict[str, Any], None]:
        try:
            yield {
                "type": "status",
                "data": {"message": f"[政策] 正在检索：{task.question}"}
            }

            rag_docs = await asyncio.to_thread(
                self.policy_rag_service.retrieve,
                query=task.question,
                entities=task.entities,
                top_k=5,
            )

            yield {
                "type": "status",
                "data": {"message": "[政策] 检索完成，正在生成中间总结"}
            }

            summary = ""

            if self.llm_client is not None and hasattr(self.llm_client, "stream_chat"):
                yield {
                    "type": "thinking",
                    "data": {"delta": f"\n【政策子任务】{task.question}\n"}
                }

                messages = self._build_messages(task, rag_docs)

                for chunk in self.llm_client.stream_chat(
                    messages=messages,
                    thinking=False
                ):
                    if chunk["type"] == "thinking":
                        yield {
                            "type": "thinking",
                            "data": {"delta": chunk["delta"]}
                        }
                    elif chunk["type"] == "answer":
                        summary += chunk["delta"]
                        yield {
                            "type": "thinking",
                            "data": {"delta": chunk["delta"]}
                        }

                yield {
                    "type": "thinking",
                    "data": {"delta": "\n"}
                }
            else:
                summary = await asyncio.to_thread(self._summarize, task, rag_docs)
                yield {
                    "type": "thinking",
                    "data": {"delta": f"\n【政策子任务】{task.question}\n{summary}\n"}
                }

            result = RagExecutionOutput(
                task=task,
                summary=summary,
                evidence=[{"source": "policy_rag", "content": doc} for doc in rag_docs],
                status="success"
            )

            yield {
                "type": "result_object",
                "data": result
            }

        except Exception as e:
            result = RagExecutionOutput(
                task=task,
                summary=f"RAG检索失败: {e}",
                evidence=[],
                status="failed"
            )
            yield {
                "type": "status",
                "data": {"message": result.summary}
            }
            yield {
                "type": "result_object",
                "data": result
            }

    def _build_messages(self, task: TaskPlan, rag_docs: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        system_prompt = """
你是医疗问答系统中的 PolicyRAG Agent。
请基于检索到的政策文本进行回复。
"""

        user_prompt = f"""
子问题：{task.question}

政策检索结果：
{json.dumps(rag_docs, ensure_ascii=False, indent=2)}
"""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _summarize(self, task: TaskPlan, rag_docs: List[Dict[str, Any]]) -> str:
        if self.llm_client is None:
            return f"已完成政策检索：{task.question}"

        messages = self._build_messages(task, rag_docs)
        return self.llm_client.chat(messages=messages, thinking=False).strip()