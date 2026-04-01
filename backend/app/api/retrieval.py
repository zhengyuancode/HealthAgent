from fastapi import APIRouter
from ..schemas.retrieval import RetrievalResult

router = APIRouter()

@router.get("/retrieve/rag")
async def retrieve_rag():
    # Placeholder for RAG retrieval
    return {"message": "RAG retrieval endpoint"}

@router.get("/retrieve/graph")
async def retrieve_graph():
    # Placeholder for graph retrieval
    return {"message": "Graph retrieval endpoint"}