from fastapi import APIRouter, Depends
from ..schemas.chat import ChatRequest, ChatResponse
from ..services.chat_service import ChatService

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, chat_service: ChatService = Depends()):
    return await chat_service.handle_chat_request(request)