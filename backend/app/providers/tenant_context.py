from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Tuple
from ..database import SessionLocal
from ..models.control import Tenant

class TenantContext:
    def __init__(self, tenant_id, control_session):
        self._ctrl = control_session
        self._tenant = control_session.get(Tenant, tenant_id)
        if not self._tenant:
            raise ValueError("tenant_not_found")

    @property
    def bucket(self) -> str:
        return (self._tenant.blob_config or {}).get("bucket") or "smartrag"

    @property
    def prefix(self) -> str:
        return (self._tenant.blob_config or {}).get("prefix") or ""

    @property
    def qdrant_collection(self) -> str:
        return f"{self._tenant.qdrant_prefix}_chunks"

    def tenant_session(self):
        engine = create_engine(self._tenant.tenant_db_url, future=True)
        return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()
