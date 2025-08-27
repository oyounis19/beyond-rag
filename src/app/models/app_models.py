from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from ..database import Base

class Document(Base):
    __tablename__ = "documents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_ref = Column(String, nullable=True)  # e.g., filename
    title = Column(String, nullable=True)
    status = Column(String, nullable=False, default="draft")  # draft/published/archived
    file_hash = Column(String, nullable=True)  # fingerprint for dedup
    storage_key = Column(String, nullable=True)  # object storage key
    extension = Column(String, nullable=True)  # e.g., pdf, txt
    effective_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    idx = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    page = Column(Integer, nullable=True)
    section_path = Column(String, nullable=True)
    hash = Column(String, nullable=False)

class Conflict(Base):
    __tablename__ = "conflicts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    new_chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False)
    existing_chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False)
    label = Column(String, nullable=False)  # entailment/neutral/contradiction
    score = Column(Float, default=0.0)
    neighbor_sim = Column(Float, nullable=True)
    judged_by = Column(String, nullable=True)  # nli|llm
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_action = Column(String, nullable=True)  # supersede|ignore
    resolver_note = Column(Text, nullable=True)

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # user|assistant|system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
