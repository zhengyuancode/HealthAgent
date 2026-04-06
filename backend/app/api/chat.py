from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import logging

from requests import Session

from app.services.orchestration.medical_workflow import build_medical_orchestrator, build_ProfileMemoryAgent, build_ConversationSummaryAgent
from app.schemas.chat_schemas import ChatRequest
from app.schemas.agent import FinalResponse
from app.db.user import User
from app.core.deps import get_current_user
from app.agents.orchestrator import MedicalOrchestrator
from app.db.session import get_db
from app.services.chat_service import ChatService
from app.services.knowledge.deps import get_chat_window_service
from app.services.chat_window_service import ChatWindowService
from app.agents.memory_agent import ConversationSummaryAgent, ProfileMemoryAgent

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=FinalResponse)
async def chat_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    medical_orchestrator: MedicalOrchestrator = Depends(build_medical_orchestrator),
):
    # 同步 run 用 to_thread 包一下
    return await asyncio.to_thread(medical_orchestrator.run, request.query)


@router.post("/chat/stream")
async def chat_stream_endpoint(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    medical_orchestrator: MedicalOrchestrator = Depends(build_medical_orchestrator),
    chat_window_service: ChatWindowService = Depends(get_chat_window_service),
    profile_memory_agent: ProfileMemoryAgent = Depends(build_ProfileMemoryAgent),
    conversation_summary_agent: ConversationSummaryAgent = Depends(build_ConversationSummaryAgent),
):
    print(current_user.username, "请求了流式接口，问题是：", request.query)
    session_obj = ChatService.get_session(
        db,
        user_id=current_user.id,
        session_id=request.session_id,
    )
    if not session_obj:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    async def process_evicted_round(evicted_round: list[dict], user_id: int):
   
        try:
            profile_memory_agent.run(evicted_round, user_id)
            conversation_summary_agent.run(round_messages = evicted_round, user_id = user_id, session_id = request.session_id)

        except Exception:
            logger.exception("处理超出窗口轮次失败")
    
    def on_complete(query: str, final_response: FinalResponse):
        ChatService.create_round(
            db,
            user_id=current_user.id,
            session_id=request.session_id,
            query=query,
            answer=final_response.answer,
        )
        
        evicted_round = chat_window_service.append_round_and_get_evicted(
            user_id=current_user.id,
            session_id=request.session_id,
            query=query,
            answer=final_response.answer,
        )
        
        if evicted_round:
            asyncio.create_task(process_evicted_round(evicted_round, current_user.id))
        
        
    return StreamingResponse(
        medical_orchestrator.stream_run(request.query, request.session_id, current_user.id, chat_window_service, on_complete=on_complete),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx 反向代理时防止缓冲
        },
    )