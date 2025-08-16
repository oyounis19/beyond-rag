from sqlalchemy.orm import Session
from sqlalchemy import text, create_engine
import json
import uuid
from urllib.parse import urlparse
from ..models.control import Tenant
from ..config import settings
from ..providers.storage import StorageProvider
from ..providers.qdrant_client import QdrantProvider

DEFAULT_BLOB = {"provider": "minio", "bucket": "smartrag", "prefix": ""}
DEFAULT_MODEL = {
    "llm": "openai",
    "embed_model": settings.embed_model,
    "nli_model": settings.nli_model,
}
DEFAULT_TOOLS = {"sql": True, "calculator": True, "tavily": False}

class TenantService:
    def __init__(self, db: Session):
        self.db = db
        self.storage = StorageProvider()
        self.qdrant = QdrantProvider()

    def create_tenant(self, name: str, tenant_db_url: str | None = None, qdrant_prefix: str | None = None,
                      blob_config: dict | None = None, model_cfg: dict | None = None, tool_config: dict | None = None) -> Tenant:
        # Prepare defaults
        qdrant_prefix = qdrant_prefix or name
        blob_config = blob_config or DEFAULT_BLOB
        model_cfg = model_cfg or DEFAULT_MODEL
        tool_config = tool_config or DEFAULT_TOOLS

        if not tenant_db_url:
            # Derive a db name from tenant
            db_name = f"tenant_{name.lower()}"
            # Construct base URL (no db)
            from urllib.parse import urlparse
            ctrl = urlparse(settings.control_db_url.replace("+psycopg", ""))
            base = f"postgresql+psycopg://{ctrl.username}:{ctrl.password}@{ctrl.hostname}:{ctrl.port}"
            tenant_db_url = f"{base}/{db_name}"
            # Create DB if not exists
            self._ensure_database(db_name, base)

        tenant = Tenant(
            name=name,
            tenant_db_url=tenant_db_url,
            qdrant_prefix=qdrant_prefix,
            blob_config=blob_config,
            model_config=model_cfg,  # store in ORM as model_config
            tool_config=tool_config,
        )
        self.db.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)

        # Bootstrap resources: bucket and qdrant collection
        bucket = blob_config.get("bucket", DEFAULT_BLOB["bucket"]) or DEFAULT_BLOB["bucket"]
        prefix = blob_config.get("prefix", "") if isinstance(blob_config, dict) else ""
        self.storage.ensure_bucket(bucket)
        self.qdrant.ensure_collection(f"{qdrant_prefix}_chunks", dim=384)

        return tenant

    def _ensure_database(self, db_name: str, base_url: str):
        # Connect to default 'postgres' database with AUTOCOMMIT and create target DB if missing
        admin_url = f"{base_url}/postgres"
        engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", future=True)
        with engine.connect() as conn:
            exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": db_name}).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))

    def update_tenant(self, tenant_id: uuid.UUID, **updates) -> Tenant:
        tenant: Tenant | None = self.db.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError("tenant_not_found")
        # Allow updating name, qdrant_prefix, blob_config, model_config, tool_config
        for key in ["name", "qdrant_prefix", "blob_config", "model_config", "tool_config"]:
            if key in updates and updates[key] is not None:
                setattr(tenant, key, updates[key])
        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def delete_tenant(self, tenant_id: uuid.UUID):
        tenant: Tenant | None = self.db.get(Tenant, tenant_id)
        if not tenant:
            return
        # Clean up Qdrant collection and MinIO prefix
        try:
            self.qdrant.drop_collection(f"{tenant.qdrant_prefix}_chunks")
        except Exception:
            pass
        try:
            blob = tenant.blob_config or DEFAULT_BLOB
            bucket = blob.get("bucket", DEFAULT_BLOB["bucket"]) or DEFAULT_BLOB["bucket"]
            prefix = blob.get("prefix", "")
            if prefix:
                self.storage.delete_prefix(bucket, prefix)
        except Exception:
            pass
        # Drop tenant database (dangerous in production; OK for MVP)
        try:
            ctrl = urlparse(settings.control_db_url.replace("+psycopg", ""))
            base = f"postgresql+psycopg://{ctrl.username}:{ctrl.password}@{ctrl.hostname}:{ctrl.port}/postgres"
            engine = create_engine(base, isolation_level="AUTOCOMMIT", future=True)
            with engine.connect() as conn:
                # terminate active connections then drop
                conn.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :db"), {"db": tenant.tenant_db_url.rsplit('/',1)[-1]})
                conn.execute(text(f'DROP DATABASE IF EXISTS "{tenant.tenant_db_url.rsplit("/",1)[-1]}"'))
        except Exception:
            pass
        # Remove row
        self.db.delete(tenant)
        self.db.commit()
