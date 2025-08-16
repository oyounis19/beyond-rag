from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
from ..database import SessionLocal
from ..providers.app_context import AppContext
from ..models.app_models import ChatSession, ChatMessage
from ..providers.llm import LLMProvider

router = APIRouter(prefix="/chat", tags=["Chat"])

llm_provider = LLMProvider()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/sessions")
def create_session(name: str | None = None, db: Session = Depends(get_db)):
    ctx = AppContext()
    s = ctx.get_db_session()
    try:
        sess = ChatSession(name=name)
        s.add(sess)
        s.commit()
        return {"session_id": str(sess.id)}
    finally:
        ctx.close_session(s)

@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db)):
    ctx = AppContext()
    s = ctx.get_db_session()
    try:
        sessions = s.query(ChatSession).order_by(ChatSession.created_at.desc()).limit(100).all()
        return [{"id": str(cs.id), "name": cs.name, "created_at": cs.created_at.isoformat()} for cs in sessions]
    finally:
        ctx.close_session(s)

@router.post("/sessions/{session_id}/messages")
def post_message(session_id: uuid.UUID, content: str, provider: str, db: Session = Depends(get_db)):
    ctx = AppContext()
    llm_provider.init_tenant(context=ctx, db=db)
    s = ctx.get_db_session()
    if not provider or provider not in llm_provider.available_providers:
        provider = "gemini"

    try:
        sess = s.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get response BEFORE adding user message to avoid including it in history
        response, sources = llm_provider.generate_response(content, provider, str(session_id))
        
        # Now add both messages
        user_msg = ChatMessage(session_id=session_id, role="user", content=content)
        s.add(user_msg)
        
        assistant_msg = ChatMessage(session_id=session_id, role="assistant", content=response)
        s.add(assistant_msg)
        s.commit()
        
        # Format sources to show only document names
        formatted_sources = []
        if sources:
            print(f"Raw sources from LLM: {sources}")
            for source in sources:
                if isinstance(source, dict) and 'source' in source:
                    formatted_sources.append({
                        "document_name": source['source'],
                        "text": source.get('text', '')
                    })
        
        print(f"Formatted sources: {formatted_sources}")
        
        return {
            "messages": [
                {"id": str(user_msg.id), "role": user_msg.role, "content": user_msg.content},
                {"id": str(assistant_msg.id), "role": assistant_msg.role, "content": assistant_msg.content}
            ],
            "sources": formatted_sources
        }
    except Exception as e:
        print(f"Error in post_message: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        ctx.close_session(s)

@router.get("/sessions/{session_id}/messages")
def list_messages(session_id: uuid.UUID, db: Session = Depends(get_db)):
    ctx = AppContext()
    s = ctx.get_db_session()
    try:
        msgs = s.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
        return [{"id": str(m.id), "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in msgs]
    finally:
        ctx.close_session(s)
