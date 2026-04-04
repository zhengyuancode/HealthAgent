from fastapi import APIRouter, Depends
from app.services.orchestration.medical_workflow import build_medical_orchestrator
from app.schemas.chat_schemas import ChatRequest
from app.schemas.agent import FinalResponse
from app.db.user import User
from app.core.deps import get_current_user
router = APIRouter()

@router.post("/chat", response_model=FinalResponse)
async def chat_endpoint(request: ChatRequest,
                        current_user: User = Depends(get_current_user),
                        medical_orchestrator = Depends(build_medical_orchestrator)):
    return await medical_orchestrator.run(request.query)