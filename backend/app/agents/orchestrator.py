import json
import asyncio
from typing import Dict, Any, List, AsyncGenerator

from qdrant_client import QdrantClient

from app.schemas.agent import (
    FinalResponse,
    RagExecutionOutput,
    GraphExecutionOutput,
    MemoryExecutionOutput,
    NoneExecutionOutput,
    AnalysisResult,
    ExecutionPlan,
)
from app.services.intake.query_analyze import QueryAnalyzerService
from app.repositories.chat_memory_repository import ChatRepository
from app.agents.planner_agent import PlannerAgent
from app.agents.medical_agent import MedicalAgent
from app.agents.policy_agent import PolicyRAGAgent
from app.llm.client import LLMClient
from app.core.config import Settings
from qdrant_client.models import Filter, FieldCondition, MatchValue
from app.db.session import SessionLocal
from app.services.chat_window_service import ChatWindowService
from app.llm.client import EmbeddingClient
from qdrant_client.models import VectorParams, Distance, Filter, FieldCondition, MatchValue



class MedicalOrchestrator:
    def __init__(
        self,
        analyzer: QueryAnalyzerService,
        planner: PlannerAgent,
        medical_agent: MedicalAgent,
        policy_rag_agent: PolicyRAGAgent,
        llm_client: LLMClient
    ):
        self.settings = Settings()
        self.analyzer = analyzer
        self.planner = planner
        self.medical_agent = medical_agent
        self.policy_rag_agent = policy_rag_agent
        self.llm_client = llm_client
        self.qdrant_client = QdrantClient(
            host=self.settings.server_ip,
            port=6333,
            timeout=120.0,
            check_compatibility=False
        )
        self.embedder = EmbeddingClient(self.settings)
        self.memory_collection_name = "conversation_summary"
        self.memory_limit = 2
        self.db = SessionLocal()
        

    @staticmethod
    def _sse(chunk: dict) -> str:
        return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

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

    async def stream_run(self, query: str, session_id: int, user_id: int, chat_window_service: ChatWindowService, on_complete=None) -> AsyncGenerator[str, None]:
        rag_results: List[RagExecutionOutput] = []
        graph_results: List[GraphExecutionOutput] = []
        memory_results: List[Dict[str, Any]] = []
        none_results: List[NoneExecutionOutput] = []

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
            plan = await asyncio.to_thread(self.planner.plan, user_id, session_id, analysis, chat_window_service)
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
                            await asyncio.sleep(0)

                elif task.knowledge_route == "policy_rag":
                    async for event in self.policy_rag_agent.stream_run(task):
                        if event["type"] == "result_object":
                            rag_results.append(event["data"])
                        else:
                            yield self._sse(event)
                            await asyncio.sleep(0)
                elif task.knowledge_route == "memory":
                    yield self._sse({
                        "type": "status",
                        "data": {"message": "正在检索历史记忆"}
                    })

                    try:
                        query = (task.question or "").strip()
                        if not query:
                            yield self._sse({
                                "type": "status",
                                "data": {"message": "历史记忆检索跳过：query 为空"}
                            })
                        else:
                            embedding_result = self.embedder.embed_content(
                                [query],
                                task="retrieval.query",
                                return_multivector=False,
                            )[0]

                            query_vector = embedding_result.get("embedding", [])

                            if not query_vector:
                                raise ValueError("memory query vector 为空")

                            if not self.qdrant_client.collection_exists(self.memory_collection_name):
                                self.qdrant_client.create_collection(
                                    collection_name=self.memory_collection_name,
                                    vectors_config=VectorParams(
                                        size=len(query_vector),
                                        distance=Distance.COSINE,
                                    ),
                                )
                                yield self._sse({
                                    "type": "status",
                                    "data": {"message": "历史记忆集合不存在，已自动创建"}
                                })

                            resp = self.qdrant_client.query_points(
                                collection_name=self.memory_collection_name,
                                query=query_vector,
                                query_filter=Filter(
                                    must=[
                                        FieldCondition(
                                            key="user_id",
                                            match=MatchValue(value=user_id),
                                        ),
                                        FieldCondition(
                                            key="type",
                                            match=MatchValue(value="chat_summary"),
                                        ),
                                    ]
                                ),
                                limit=self.memory_limit,
                                with_payload=True,
                                with_vectors=False,
                            )

                            points = getattr(resp, "points", []) or []
                            if not points:
                                yield self._sse({
                                    "type": "status",
                                    "data": {"message": "未检索到相关历史记忆"}
                                })

                            for p in points:
                                payload = p.payload or {}
                                summary = payload.get("summary", "")
                                res = self.llm_client.chat_json([
                                    {
                                        "role": "system",
                                        "content": "你是一个助手，只返回合法 JSON 对象。"
                                    },
                                    {
                                        "role": "user",
                                        "content": f'''
                                        你是一个摘要相关判断器
                                        请判断当前摘要是否有助于回答当前问题
                                        
                                        如果当前摘要对回答当前问题无用，输出：
                                        {{
                                            "need": False
                                        }}
                                        
                                        如果当前摘要对回答当前的问题有用，输出：
                                        {{
                                            "need": True
                                        }}
                                        
                                        当前问题：
                                        {query}
                                        
                                        历史对话：
                                        {json.dumps(chat_window_service.get_rounds(user_id=user_id, session_id=session_id), ensure_ascii=False, indent=2)} 
                                        
                                        当前摘要：
                                        {summary}  
                                        '''
                                    }
                                ])
                                need = bool(res.get("need"))
                                if need:
                                    memory_results.append(MemoryExecutionOutput(
                                        task=task,
                                        summary=summary,
                                        status="success"
                                    ))
                                    yield self._sse({
                                        "type": "status",
                                        "data": {"message": summary}
                                    })
                            if len(memory_results) == 0:
                                yield self._sse({
                                    "type": "status",
                                    "data": {"message": "未检索到相关历史记忆"}
                                })
                    except Exception as e:
                        print(f"memory search error:{e}")
                        yield self._sse({
                            "type": "error",
                            "data": {"message": f"历史记忆检索失败: {str(e)}"}
                        })
                elif task.knowledge_route == "none":
                    none_results.append(NoneExecutionOutput(
                            task=task,
                            summary="该子任务不需要检索，直接回答: " + task.question,
                            status="success"
                        ))

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
                user_id, session_id, query, chat_window_service, analysis, plan, rag_results, graph_results, memory_results, none_results
            ):
                if chunk["type"] == "answer":
                    answer += chunk["delta"]

                yield self._sse(chunk)
                await asyncio.sleep(0)

            final_response = FinalResponse(
                answer=answer,
                risk_level=analysis.risk_level,
                analysis=analysis,
                plan=plan,
                rag_results=rag_results,
                graph_results=graph_results
            )
            
            if on_complete:
                result = on_complete(query, final_response)
                if asyncio.iscoroutine(result):
                    await result

    
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
        user_id: int,
        session_id: int,
        query: str,
        chat_window_service: ChatWindowService,
        analysis: AnalysisResult,
        plan: ExecutionPlan,
        rag_results: List[RagExecutionOutput],
        graph_results: List[GraphExecutionOutput],
        memory_results: List[MemoryExecutionOutput],
        none_results: List[NoneExecutionOutput]
    ) -> AsyncGenerator[str, None]:
        success_results = [r for r in (rag_results + graph_results + memory_results + none_results) if r.status == "success"]


        if self.llm_client is None or not hasattr(self.llm_client, "stream_chat"):
            text = self._build_fallback_answer(success_results)
            yield {
                    "type": "answer",
                    "delta": text
                }
            return

        summaries = []
        if len(success_results) != 0:
            for idx, result in enumerate(success_results, start=1):
                summaries.append(f"{idx}. {result.summary}")
            
        profile = ChatRepository.get_user_profile_dict(
            self.db,
            user_id=user_id
        )
        system_prompt = """
    你是医疗问答系统中的总结助手。
    请基于已完成的子任务结果，回答用户当前问题。

    要求：
    1. 只能依据提供的历史对话、用户画像和子任务结果回答
    2. 回答清晰、自然、适合直接给用户看
    3. 不要编造知识库中没有的信息
    4. 如果证据不足，要明确说“目前证据不足”
    5. 医疗相关表述要谨慎，避免绝对化诊断
    6. 只回答日常问候及医疗相关问题，其他问题请拒绝回答
    7. 不要完全依赖子任务结果，有可能子任务结果有误差，适当结合问题分析和执行计划进行综合判断
    """

        user_prompt = f"""
    用户画像：
    {json.dumps(profile, ensure_ascii=False, indent=2)}
    
    历史对话：
    {json.dumps(chat_window_service.get_rounds(user_id=user_id, session_id=session_id), ensure_ascii=False, indent=2)}
    
    用户当前问题：
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

        for s in self.llm_client.stream_chat(messages=messages, thinking=False):
            yield s

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