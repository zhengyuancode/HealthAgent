from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import asyncio

from app.services.orchestration.medical_workflow import build_medical_orchestrator
from app.schemas.chat_schemas import ChatRequest
from app.schemas.agent import FinalResponse
from app.db.user import User
from app.core.deps import get_current_user
from app.agents.orchestrator import MedicalOrchestrator

router = APIRouter()


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
    current_user: User = Depends(get_current_user),
    medical_orchestrator: MedicalOrchestrator = Depends(build_medical_orchestrator),
):
    return StreamingResponse(
        medical_orchestrator.stream_run(request.query),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx 反向代理时防止缓冲
        },
    )