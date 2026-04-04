import json
from typing import Any, Dict

from app.schemas.agent import AnalysisResult, GraphExecutionOutput, TaskPlan
from app.services.knowledge.interfaces import MedicalGraphService
from app.services.knowledge.schema_retriever import QdrantSchemaRetriever


class MedicalAgent:
    name = "medical_agent"

    def __init__(self, llm_client, graph_service: MedicalGraphService, retriver: QdrantSchemaRetriever):
        self.graph_service = graph_service
        self.llm_client = llm_client
        self.retriver = retriver

    def run(
        self,
        task: TaskPlan
    ) -> GraphExecutionOutput:
        try:
            graph_result = self.graph_service.query(
                query=task.question,
                retriever=self.retriver,
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

    def _summarize(self, task: TaskPlan, graph_result: Dict[str, Any]) -> str:
        if self.llm_client is None:
            return f"已完成图谱推理：{task.question}"

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
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.llm_client.chat(messages=messages, thinking=False).strip()