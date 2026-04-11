from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from rag_app.services.rag import RAGService

router = APIRouter()

# Lazy initialization
_rag_service = None

def get_rag_service():
    """Get or create RAG service (lazy initialization)."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    context: list[str]
    sources: list[str]

@router.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest, rag_service: RAGService = Depends(get_rag_service)):
    """Ask a question against uploaded documents."""
    try:
        result = rag_service.query(request.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query failed: {str(e)}")

