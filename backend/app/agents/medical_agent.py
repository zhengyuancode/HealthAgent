import json
import asyncio
from typing import Any, Dict, AsyncGenerator, List

from app.schemas.agent import GraphExecutionOutput, TaskPlan
from app.services.knowledge.interfaces import MedicalGraphService


class MedicalAgent:
    name = "medical_agent"

    def __init__(self, llm_client, graph_service: MedicalGraphService):
        self.graph_service = graph_service
        self.llm_client = llm_client

    def run(self, task: TaskPlan) -> GraphExecutionOutput:
        try:
            graph_result = self.graph_service.query(
                query=task.question,
                entities=task.entities,
                semantic_type=task.semantic_type,
                topk=5,
                topn=5
            )

            summary = self._summarize(task, graph_result)

            return GraphExecutionOutput(
                task=task,
                summary=summary,
                evidence=[{"source": "graph", "content": graph_result}],
                status="success"
            )
        except Exception as e:
            return GraphExecutionOutput(
                task=task,
                summary=f"图谱检索失败: {e}",
                evidence=[],
                status="failed"
            )

    async def stream_run(self, task: TaskPlan) -> AsyncGenerator[Dict[str, Any], None]:
        try:
            yield {
                "type": "status",
                "data": {"message": f"[图谱] 正在检索：{task.question}"}
            }

            graph_result = await asyncio.to_thread(
                self.graph_service.query,
                query=task.question,
                entities=task.entities,
                semantic_type=task.semantic_type,
                topk=5,
                topn=5
            )

            yield {
                "type": "status",
                "data": {"message": "[图谱] 检索完成，正在生成中间总结"}
            }

            summary = ""

            if self.llm_client is not None and hasattr(self.llm_client, "stream_chat"):
                yield {
                    "type": "thinking",
                    "data": {"delta": f"\n【图谱子任务】{task.question}\n"}
                }

                messages = self._build_messages(task, graph_result)

                for chunk in self.llm_client.stream_chat(
                    messages=messages,
                    thinking=False
                ):
                    if chunk["type"] == "thinking":
                        yield {
                            "type": "thinking",
                            "delta": chunk["delta"]
                        }
                    elif chunk["type"] == "answer":
                        summary += chunk["delta"]
                        yield {
                            "type": "thinking",
                            "delta": chunk["delta"]
                        }

                yield {
                    "type": "thinking",
                    "delta": "\n"
                }
            else:
                summary = await asyncio.to_thread(self._summarize, task, graph_result)
                yield {
                    "type": "thinking",
                    "data": {"delta": f"\n【图谱子任务】{task.question}\n{summary}\n"}
                }

            result = GraphExecutionOutput(
                task=task,
                summary=summary,
                evidence=[{"source": "graph", "content": graph_result}],
                status="success"
            )

            yield {
                "type": "result_object",
                "data": result
            }

        except Exception as e:
            result = GraphExecutionOutput(
                task=task,
                summary=f"图谱检索失败: {e}",
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

    def _build_messages(self, task: TaskPlan, graph_result: Dict[str, Any]) -> List[Dict[str, str]]:
        system_prompt = """
你是医疗问答系统中的 Medical Agent。
请基于提供的知识图谱检索结果回答子问题。

要求：
1. 只能依据图谱结果回答
2. 优先使用 graph_results 中的关系证据
3. 如果只匹配到节点、但没有关系结果，要明确说明图谱中未检索到足够关系证据
4. 不要输出无依据诊断
5. 不要夸大确定性
"""

        user_prompt = f"""
子问题：{task.question}
问题类型：{task.semantic_type}

图谱结果：
{json.dumps(graph_result, ensure_ascii=False, indent=2)}
"""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _summarize(self, task: TaskPlan, graph_result: Dict[str, Any]) -> str:
        if self.llm_client is None:
            return f"已完成图谱推理：{task.question}"

        messages = self._build_messages(task, graph_result)
        return self.llm_client.chat(messages=messages, thinking=False).strip()