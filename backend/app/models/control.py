from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from ..database import Base

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    tenant_db_url = Column(String, nullable=False)
    qdrant_prefix = Column(String, nullable=False)
    blob_config = Column(JSON, nullable=False, default=dict)  # bucket, prefix
    model_config = Column(JSON, nullable=False, default=dict)  # llm, embeddings, nli
    tool_config = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
