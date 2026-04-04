import json
import asyncio
from typing import Dict, Any, List, AsyncGenerator

from app.schemas.agent import (
    FinalResponse,
    RagExecutionOutput,
    GraphExecutionOutput,
    AnalysisResult,
    ExecutionPlan,
)
from app.services.intake.query_analyze import QueryAnalyzerService
from app.agents.planner_agent import PlannerAgent
from app.agents.medical_agent import MedicalAgent
from app.agents.policy_agent import PolicyRAGAgent
from app.llm.client import LLMClient


class MedicalOrchestrator:
    def __init__(
        self,
        analyzer: QueryAnalyzerService,
        planner: PlannerAgent,
        medical_agent: MedicalAgent,
        policy_rag_agent: PolicyRAGAgent,
        llm_client: LLMClient
    ):
        self.analyzer = analyzer
        self.planner = planner
        self.medical_agent = medical_agent
        self.policy_rag_agent = policy_rag_agent
        self.llm_client = llm_client

    @staticmethod
    def _sse(data: Dict[str, Any]) -> str:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    def run(self, query: str) -> FinalResponse:
        analysis = self.analyzer.analyze(query)
        plan = self.planner.plan(analysis)

        rag_results: List[RagExecutionOutput] = []
        graph_results: List[GraphExecutionOutput] = []

        for task in plan.tasks:
            result = self._run_task(task)

            if task.knowledge_route == "policy_rag":
                rag_results.append(result)
            elif task.knowledge_route == "medical_graph":
                graph_results.append(result)

        answer = self._synthesize(query, analysis, plan, rag_results, graph_results)

        return FinalResponse(
            answer=answer,
            risk_level=analysis.risk_level,
            analysis=analysis,
            plan=plan,
            rag_results=rag_results,
            graph_results=graph_results
        )

    async def stream_run(self, query: str) -> AsyncGenerator[str, None]:
        rag_results: List[RagExecutionOutput] = []
        graph_results: List[GraphExecutionOutput] = []

        try:
            yield self._sse({
                "type": "status",
                "data": {"message": "正在分析问题"}
            })
            analysis = await asyncio.to_thread(self.analyzer.analyze, query)

            yield self._sse({
                "type": "status",
                "data": {"message": "正在生成执行计划"}
            })
            plan = await asyncio.to_thread(self.planner.plan, analysis)

            yield self._sse({
                "type": "plan",
                "data": plan.model_dump()
            })

            for idx, task in enumerate(plan.tasks, start=1):
                yield self._sse({
                    "type": "status",
                    "data": {
                        "message": f"正在执行子任务 {idx}/{len(plan.tasks)}：{task.question}"
                    }
                })

                if task.knowledge_route == "medical_graph":
                    async for event in self.medical_agent.stream_run(task):
                        if event["type"] == "result_object":
                            graph_results.append(event["data"])
                        else:
                            yield self._sse(event)

                elif task.knowledge_route == "policy_rag":
                    async for event in self.policy_rag_agent.stream_run(task):
                        if event["type"] == "result_object":
                            rag_results.append(event["data"])
                        else:
                            yield self._sse(event)

                else:
                    yield self._sse({
                        "type": "status",
                        "data": {
                            "message": f"未知知识路由：{task.knowledge_route}，已跳过"
                        }
                    })

            yield self._sse({
                "type": "status",
                "data": {"message": "正在生成最终回答"}
            })

            answer = ""
            async for chunk in self._stream_synthesize(
                query, analysis, plan, rag_results, graph_results
            ):
                answer += chunk
                yield self._sse({
                    "type": "answer",
                    "data": {"delta": chunk}
                })

            final_response = FinalResponse(
                answer=answer,
                risk_level=analysis.risk_level,
                analysis=analysis,
                plan=plan,
                rag_results=rag_results,
                graph_results=graph_results
            )

            yield self._sse({
                "type": "done",
                "data": {"final_response": final_response.model_dump()}
            })

        except Exception as e:
            yield self._sse({
                "type": "error",
                "data": {"message": f"流式执行失败: {str(e)}"}
            })

    def _run_task(self, task):
        if task.knowledge_route == "medical_graph":
            return self.medical_agent.run(task)

        if task.knowledge_route == "policy_rag":
            return self.policy_rag_agent.run(task)

        raise ValueError(f"未知知识路由: {task.knowledge_route}")

    async def _stream_synthesize(
        self,
        query: str,
        analysis: AnalysisResult,
        plan: ExecutionPlan,
        rag_results: List[RagExecutionOutput],
        graph_results: List[GraphExecutionOutput]
    ) -> AsyncGenerator[str, None]:
        success_results = [r for r in (rag_results + graph_results) if r.status == "success"]

        if not success_results:
            text = "当前没有获得足够的知识库结果，建议补充更具体的问题描述后再试。"
            for ch in text:
                yield ch
            return

        if self.llm_client is None or not hasattr(self.llm_client, "stream_chat"):
            text = self._build_fallback_answer(success_results)
            for ch in text:
                yield ch
            return

        summaries = []
        for idx, result in enumerate(success_results, start=1):
            summaries.append(f"{idx}. {result.summary}")

        system_prompt = """
    你是医疗问答系统中的总结助手。
    请基于已完成的子任务结果，生成最终答复。

    要求：
    1. 只能依据提供的子任务结果回答
    2. 回答清晰、自然、适合直接给用户看
    3. 不要编造知识库中没有的信息
    4. 如果证据不足，要明确说“目前证据不足”
    5. 医疗相关表述要谨慎，避免绝对化诊断
    """

        user_prompt = f"""
    用户问题：
    {query}

    问题分析：
    {analysis.model_dump_json(indent=2, ensure_ascii=False)}

    执行计划：
    {plan.model_dump_json(indent=2, ensure_ascii=False)}

    子任务结果摘要：
    {chr(10).join(summaries)}
    """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        for chunk in self.llm_client.stream_chat(messages=messages, thinking=False):
            if chunk["type"] == "answer":
                yield chunk["delta"]

    def _synthesize(
        self,
        query: str,
        analysis: AnalysisResult,
        plan: ExecutionPlan,
        rag_results: List[RagExecutionOutput],
        graph_results: List[GraphExecutionOutput]
    ) -> str:
        success_results = [r for r in (rag_results + graph_results) if r.status == "success"]

        if not success_results:
            return "当前没有获得足够的知识库结果，建议补充更具体的问题描述后再试。"

        if self.llm_client is None:
            return self._build_fallback_answer(success_results)

        summaries = []
        for idx, result in enumerate(success_results, start=1):
            summaries.append(f"{idx}. {result.summary}")

        system_prompt = """
    你是医疗问答系统中的总结助手。
    请基于已完成的子任务结果，生成最终答复。

    要求：
    1. 只能依据提供的子任务结果回答
    2. 回答清晰、自然、适合直接给用户看
    3. 不要编造知识库中没有的信息
    4. 如果证据不足，要明确说“目前证据不足”
    5. 医疗相关表述要谨慎，避免绝对化诊断
    """

        user_prompt = f"""
    用户问题：
    {query}

    问题分析：
    {analysis.model_dump_json(indent=2, ensure_ascii=False)}

    执行计划：
    {plan.model_dump_json(indent=2, ensure_ascii=False)}

    子任务结果摘要：
    {chr(10).join(summaries)}
    """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        return self.llm_client.chat(messages=messages, thinking=False).strip()