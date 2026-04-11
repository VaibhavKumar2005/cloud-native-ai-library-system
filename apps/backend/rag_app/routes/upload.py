from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
import os
from rag_app.services.document import DocumentService
from rag_app.services.rag import RAGService

router = APIRouter()

# Lazy initialization
_doc_service = None
_rag_service = None

def get_doc_service():
    """Get or create document service."""
    global _doc_service
    if _doc_service is None:
        _doc_service = DocumentService()
    return _doc_service

def get_rag_service():
    """Get or create RAG service."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service

class UploadResponse(BaseModel):
    filename: str
    chunks_count: int
    status: str

@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    doc_service: DocumentService = Depends(get_doc_service),
    rag_service: RAGService = Depends(get_rag_service)
):
    """Upload a PDF or text document for RAG processing."""
    try:
        # Save uploaded file temporarily
        temp_path = f"/tmp/{file.filename}"
        os.makedirs("/tmp", exist_ok=True)
        
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)
        
        # Extract text and create embeddings
        chunks = doc_service.process_document(temp_path, file.filename)
        
        # Add to RAG index
        rag_service.add_documents(chunks, file.filename)
        
        # Clean up
        os.remove(temp_path)
        
        return UploadResponse(
            filename=file.filename,
            chunks_count=len(chunks),
            status="success"
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")

