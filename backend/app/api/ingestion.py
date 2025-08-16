import uuid
import asyncio
import json

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..providers.app_context import AppContext
from ..services.ingestion_service import IngestionService

router = APIRouter(prefix="/documents", tags=["Documents"])

svc = IngestionService()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("")
def upload_document(file: UploadFile | str = File(...), title: str | None = Form(None), db: Session = Depends(get_db)):
    ctx = AppContext()
    svc.init_tenant(context=ctx, db=db)
    doc = svc.ingest(file=file, title=title)
    return doc


@router.post("/{document_id}/publish")
async def publish_document(document_id: uuid.UUID, docling: bool = False, db: Session = Depends(get_db)):
    ctx = AppContext()
    svc.init_tenant(context=ctx, db=db)
    res = await svc.publish(document_id, docling=docling)
    return res


@router.get("")
def list_documents(db: Session = Depends(get_db)):
    ctx = AppContext()
    svc.init_tenant(context=ctx, db=db)
    return svc.list_documents()

@router.get("/{document_id}")
def get_document_chunks(document_id: uuid.UUID, db: Session = Depends(get_db)):
    ctx = AppContext()
    svc.init_tenant(context=ctx, db=db)
    chunks = svc.get_document_chunks(document_id)
    if not chunks:
        raise HTTPException(status_code=404, detail="Document not found")
    return chunks

@router.get("/{document_id}/status")
def document_status(document_id: uuid.UUID, db: Session = Depends(get_db)):
    ctx = AppContext()
    svc.init_tenant(context=ctx, db=db)
    status = svc.document_status(document_id)
    if not status:
        raise HTTPException(status_code=404, detail="Document not found")
    return status

@router.delete("/{document_id}")
def delete_document(document_id: uuid.UUID, db: Session = Depends(get_db)):
    ctx = AppContext()
    svc.init_tenant(context=ctx, db=db)
    result = svc.delete_document(document_id)
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"ok": True, "document_id": str(document_id), "deleted": True}

@router.get("/{document_id}/publish-stream")
async def publish_document_stream(document_id: uuid.UUID, docling: bool = False):
    """Stream publishing progress using Server-Sent Events"""
    async def event_generator():
        try:
            ctx = AppContext()
            svc = IngestionService()
            svc.init_tenant(context=ctx, db=None)
            
            # Use the streaming version of publish
            async for event in svc.publish_document_stream(document_id, docling=docling):
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0.01)  # Small delay to prevent overwhelming the client
                
        except Exception as e:
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"SSE publish error for document {document_id}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            error_event = {
                "stage": "error",
                "error": str(e),
                "ok": False,
                "message": f"Publishing failed: {str(e)}"
            }
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )
