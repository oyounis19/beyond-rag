import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ..database import SessionLocal
from ..providers.app_context import AppContext
from ..models.app_models import Conflict, Chunk
from ..providers.qdrant_client import QdrantProvider
from ..services.ingestion_service import IngestionService

router = APIRouter(prefix="/conflicts", tags=["Conflicts"])

qdrant = QdrantProvider()
ingestion_service = IngestionService()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("")
def list_conflicts(db: Session = Depends(get_db)):
    ctx = AppContext()
    s = ctx.get_db_session()
    try:
        # Get unresolved contradictions and fetch chunk texts separately
        contradictions = s.query(Conflict).filter(Conflict.resolved_at.is_(None)).limit(200).all()
        
        result = []
        for contradiction in contradictions:
            # Get chunk texts separately to avoid join alias conflicts
            new_chunk = s.query(Chunk).filter(Chunk.id == contradiction.new_chunk_id).first()
            existing_chunk = s.query(Chunk).filter(Chunk.id == contradiction.existing_chunk_id).first()
            
            result.append({
                "id": str(contradiction.id),
                "new_chunk_id": str(contradiction.new_chunk_id),
                "existing_chunk_id": str(contradiction.existing_chunk_id),
                "label": contradiction.label,
                "score": contradiction.score,
                "neighbor_sim": contradiction.neighbor_sim,
                "judged_by": contradiction.judged_by,
                "resolution_action": contradiction.resolution_action,
                "new_chunk_text": new_chunk.text if new_chunk else "Content not available",
                "existing_chunk_text": existing_chunk.text if existing_chunk else "Content not available",
            })
        return result
    finally:
        ctx.close_session(s)

@router.post("/{conflict_id}/resolve")
def resolve_conflict(conflict_id: uuid.UUID, action: str = "ignore", note: str | None = None, db: Session = Depends(get_db)):
    if action not in {"ignore", "supersede"}:
        raise HTTPException(status_code=400, detail="Invalid action")
    ctx = AppContext()
    s = ctx.get_db_session()
    try:
        c = s.query(Conflict).filter(Conflict.id == conflict_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Conflict not found")
        
        # Get the conflicting chunks
        new_chunk = s.query(Chunk).filter(Chunk.id == c.new_chunk_id).first()
        existing_chunk = s.query(Chunk).filter(Chunk.id == c.existing_chunk_id).first()
        
        if not new_chunk or not existing_chunk:
            raise HTTPException(status_code=404, detail="Conflicting chunks not found")
        
        # Extract information we need before any deletions
        conflict_id_str = str(c.id)
        new_chunk_id = c.new_chunk_id
        existing_chunk_id = c.existing_chunk_id
        
        ingestion_service.init_tenant(context=ctx, db=s)
        
        # Apply the resolution action
        if action == "supersede":
            # Apply new: Delete the existing chunk, keep the new one
            chunk_to_delete = existing_chunk
            chunk_to_keep = new_chunk
            document_id = new_chunk.document_id
        else:  # action == "ignore"
            # Keep existing: Delete the new chunk, keep the existing one
            chunk_to_delete = new_chunk
            chunk_to_keep = existing_chunk
            document_id = existing_chunk.document_id
        
        chunk_to_delete_id = str(chunk_to_delete.id)
        chunk_to_keep_id = str(chunk_to_keep.id)
        
        # Mark conflict as resolved BEFORE deleting chunks
        c.resolution_action = action
        c.resolved_at = datetime.now(timezone.utc)
        c.resolver_note = note or f"Applied {action}: kept chunk {chunk_to_keep_id}, removed chunk {chunk_to_delete_id}"
        
        # Commit the conflict resolution first
        s.commit()
        
        # Delete the chunk from Qdrant
        try:
            qdrant.client.delete(
                collection_name=ctx.qdrant_collection,
                points_selector=[chunk_to_delete_id]
            )
        except Exception as e:
            print(f"Warning: Failed to delete chunk {chunk_to_delete_id} from Qdrant: {e}")
        
        # Delete the chunk from database (CASCADE will handle embeddings_meta)
        s.delete(chunk_to_delete)
        s.commit()
        
        # Check if the document can be published now
        auto_published = ingestion_service._check_and_publish_if_ready(document_id, s)
        
        return {
            "id": conflict_id_str, 
            "resolved": True, 
            "action": action,
            "kept_chunk_id": chunk_to_keep_id,
            "removed_chunk_id": chunk_to_delete_id,
            "auto_published": auto_published
        }
        
    finally:
        ctx.close_session(s)

@router.post("/resolve-all")
def resolve_all_conflicts(action: str = "supersede", note: str | None = None, db: Session = Depends(get_db)):
    """Apply new changes to all conflicting chunks (bulk resolution)"""
    if action not in {"ignore", "supersede"}:
        raise HTTPException(status_code=400, detail="Invalid action")
    ctx = AppContext()
    s = ctx.get_db_session()
    try:
        # Get all unresolved contradictions
        unresolved = s.query(Conflict).filter(Conflict.resolved_at.is_(None)).all()
        if not unresolved:
            return {"resolved_count": 0, "message": "No conflicts to resolve"}
        
        now = datetime.now(timezone.utc)
        
        # Track which documents might need publishing and chunks to delete
        affected_documents = set()
        chunks_to_delete = []
        chunks_kept = []
        chunks_removed = []
        
        ingestion_service.init_tenant(context=ctx, db=s)
        
        for c in unresolved:
            # Get the conflicting chunks
            new_chunk = s.query(Chunk).filter(Chunk.id == c.new_chunk_id).first()
            existing_chunk = s.query(Chunk).filter(Chunk.id == c.existing_chunk_id).first()
            
            if not new_chunk or not existing_chunk:
                continue  # Skip if chunks are missing
            
            # Determine which chunk to delete based on action
            if action == "supersede":
                # Apply new: Delete the existing chunk, keep the new one
                chunk_to_delete = existing_chunk
                chunk_to_keep = new_chunk
                document_id = new_chunk.document_id
            else:  # action == "ignore"
                # Keep existing: Delete the new chunk, keep the existing one
                chunk_to_delete = new_chunk
                chunk_to_keep = existing_chunk
                document_id = existing_chunk.document_id
            
            chunks_to_delete.append(chunk_to_delete)
            chunks_kept.append(str(chunk_to_keep.id))
            chunks_removed.append(str(chunk_to_delete.id))
            affected_documents.add(document_id)
            
            # Mark conflict as resolved
            c.resolution_action = action
            c.resolved_at = now
            c.resolver_note = note or f"Bulk resolution: {action} - kept {chunk_to_keep.id}, removed {chunk_to_delete.id}"
        
        # Delete chunks from Qdrant in batch
        if chunks_to_delete:
            try:
                chunk_ids_to_delete = [str(chunk.id) for chunk in chunks_to_delete]
                qdrant.client.delete(
                    collection_name=ctx.qdrant_collection,
                    points_selector=chunk_ids_to_delete
                )
            except Exception as e:
                print(f"Warning: Failed to delete chunks from Qdrant: {e}")
        
        # Delete chunks from database
        for chunk in chunks_to_delete:
            s.delete(chunk)
        
        s.commit()
        
        # Check if any documents can be auto-published
        auto_published_docs = []
        for doc_id in affected_documents:
            if ingestion_service._check_and_publish_if_ready(doc_id, s):
                auto_published_docs.append(str(doc_id))
        
        return {
            "resolved_count": len(unresolved), 
            "action": action,
            "chunks_kept": chunks_kept,
            "chunks_removed": chunks_removed,
            "auto_published_documents": auto_published_docs
        }
    finally:
        ctx.close_session(s)
