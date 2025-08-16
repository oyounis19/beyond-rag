from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Float, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

TenantBase = declarative_base()

class Document(TenantBase):
    __tablename__ = "documents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_ref = Column(String, nullable=True)  # user-provided stable ref (e.g., filename)
    title = Column(String, nullable=True)
    status = Column(String, nullable=False, default="draft")  # draft/published/archived
    file_hash = Column(String, nullable=True)  # fingerprint for dedup
    storage_key = Column(String, nullable=True)  # object storage key
    extension = Column(String, nullable=True)  # e.g., pdf, txt
    effective_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Chunk(TenantBase):
    __tablename__ = "chunks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    idx = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    page = Column(Integer, nullable=True)
    section_path = Column(String, nullable=True)
    hash = Column(String, nullable=False)

class EmbeddingMeta(TenantBase):
    __tablename__ = "embeddings_meta"
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"), primary_key=True)
    model = Column(String, nullable=False)
    dim = Column(Integer, nullable=False)
    last_embedded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Conflict(TenantBase):
    __tablename__ = "contradictions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    new_chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False)
    existing_chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False)
    label = Column(String, nullable=False)  # entailment/neutral/contradiction
    score = Column(Float, nullable=False)
    neighbor_sim = Column(Float, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_action = Column(String, nullable=True)  # supersede|ignore
    resolver_note = Column(Text, nullable=True)

class DedupGroup(TenantBase):
    __tablename__ = "dedup_groups"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    representative_chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True)

class DedupGroupMember(TenantBase):
    __tablename__ = "dedup_group_members"
    group_id = Column(UUID(as_uuid=True), ForeignKey("dedup_groups.id", ondelete="CASCADE"), primary_key=True)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"), primary_key=True)

class ToolConfig(TenantBase):
    __tablename__ = "tool_configs"
    tool_name = Column(String, primary_key=True)
    enabled = Column(Boolean, nullable=False, default=True)
    config_json = Column(JSON, nullable=True)

class ChatSession(TenantBase):
    __tablename__ = "chat_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ChatMessage(TenantBase):
    __tablename__ = "chat_messages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # user|assistant|system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class EvalTest(TenantBase):
    __tablename__ = "eval_tests"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    question = Column(Text, nullable=False)
    expected = Column(Text, nullable=True)
    tags = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class EvalRun(TenantBase):
    __tablename__ = "eval_runs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trigger = Column(String, nullable=False)  # publish|manual|schedule
    summary_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class EvalRunResult(TenantBase):
    __tablename__ = "eval_run_results"
    run_id = Column(UUID(as_uuid=True), ForeignKey("eval_runs.id", ondelete="CASCADE"), primary_key=True)
    test_id = Column(UUID(as_uuid=True), ForeignKey("eval_tests.id", ondelete="CASCADE"), primary_key=True)
    answer = Column(Text, nullable=True)
    metrics_json = Column(JSON, nullable=True)
