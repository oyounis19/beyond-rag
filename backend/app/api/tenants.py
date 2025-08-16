from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal, engine, Base
from ..schemas.tenant import TenantCreate, TenantOut, TenantUpdate
from ..services.tenant_service import TenantService
from ..models.tenant_db import TenantBase, ToolConfig
from sqlalchemy import create_engine as create_tenant_engine
import uuid

router = APIRouter(prefix="/tenants", tags=["tenants"])

# Ensure control-plane tables exist (simple create_all for MVP)
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create Tenant
@router.post("", response_model=TenantOut)
def create_tenant(payload: TenantCreate, db: Session = Depends(get_db)):
    svc = TenantService(db)
    tenant = svc.create_tenant(
        name=payload.name,
        tenant_db_url=payload.tenant_db_url,
        qdrant_prefix=payload.qdrant_prefix,
        blob_config=payload.blob_config,
        model_cfg=payload.model_cfg,
        tool_config=payload.tool_config,
    )
    # Apply tenant DB schema immediately
    t_engine = create_tenant_engine(tenant.tenant_db_url, future=True)
    TenantBase.metadata.create_all(bind=t_engine)
    # Initialize tool configs if missing (static defaults)
    with t_engine.connect() as conn:
        existing = conn.execute(ToolConfig.__table__.select()).fetchall()
        if not existing:
            for tool_name in ["sql", "calculator", "tavily"]:
                conn.execute(ToolConfig.__table__.insert().values(tool_name=tool_name, enabled=True, config_json=None))
    return tenant


# List Tenants
@router.get("", response_model=list[TenantOut])
def list_tenants(db: Session = Depends(get_db)):
    from ..models.control import Tenant
    return db.query(Tenant).order_by(Tenant.created_at.desc()).all()

# Get Tenant by ID
@router.get("/{tenant_id}", response_model=TenantOut)
def get_tenant(tenant_id: uuid.UUID, db: Session = Depends(get_db)):
    from ..models.control import Tenant
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant

# Update Tenant
@router.patch("/{tenant_id}", response_model=TenantOut)
def update_tenant(tenant_id: uuid.UUID, payload: TenantUpdate, db: Session = Depends(get_db)):
    svc = TenantService(db)
    try:
        data = payload.model_dump(exclude_unset=True, by_alias=True)
        # Map alias back
        if "model_config" in data:
            data["model_config"] = data.pop("model_config")
        tenant = svc.update_tenant(tenant_id, **data)
        return tenant
    except ValueError:
        raise HTTPException(status_code=404, detail="Tenant not found")

# Delete Tenant
@router.delete("/{tenant_id}", status_code=204)
def delete_tenant(tenant_id: uuid.UUID, db: Session = Depends(get_db)):
    svc = TenantService(db)
    svc.delete_tenant(tenant_id)
    return None

# Tools endpoints (static scaffolds)
@router.get("/{tenant_id}/tools")
def list_tools(tenant_id: uuid.UUID, db: Session = Depends(get_db)):
    from ..models.control import Tenant
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    # Open tenant DB and read tool configs
    t_engine = create_tenant_engine(tenant.tenant_db_url, future=True)
    with t_engine.connect() as conn:
        rows = conn.execute(ToolConfig.__table__.select()).fetchall()
        return [{"tool_name": r.tool_name, "enabled": r.enabled, "config": r.config_json} for r in rows]

@router.patch("/{tenant_id}/tools/{tool_name}")
def update_tool(tenant_id: uuid.UUID, tool_name: str, enabled: bool | None = None, db: Session = Depends(get_db)):
    from ..models.control import Tenant
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    t_engine = create_tenant_engine(tenant.tenant_db_url, future=True)
    with t_engine.connect() as conn:
        stmt = ToolConfig.__table__.select().where(ToolConfig.tool_name == tool_name)
        existing = conn.execute(stmt).fetchone()
        if not existing:
            conn.execute(ToolConfig.__table__.insert().values(tool_name=tool_name, enabled=bool(enabled), config_json=None))
        else:
            if enabled is not None:
                conn.execute(ToolConfig.__table__.update().where(ToolConfig.tool_name == tool_name).values(enabled=enabled))
    return {"tool_name": tool_name, "enabled": enabled if enabled is not None else True}
