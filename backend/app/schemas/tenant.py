from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
import uuid

class TenantCreate(BaseModel):
    # model_config = ConfigDict(populate_by_name=True)
    name: str
    tenant_db_url: Optional[str] = None
    qdrant_prefix: Optional[str] = None
    blob_config: Optional[Dict[str, Any]] = None
    # Reserved name `model_config` -> use internal name with alias for input
    model_cfg: Optional[Dict[str, Any]] = Field(default=None, validation_alias='model_config')
    tool_config: Optional[Dict[str, Any]] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
            {
                "name": "Diverse",
                "tenant_db_url": "",
                "qdrant_prefix": "diverse_",
                "blob_config": {
                    "provider": "minio",
                    "bucket": "diverse-bucket",
                    "prefix": "diverse_"
                },
                "model_config": {},
                "tool_config": {
                    "sql": True,
                    "calculator": True,
                    "tavily": False
                }
            },
            {
                "name": "example_tenant",
                "tenant_db_url": "postgresql://user:password@localhost:5432/example_db",
                "qdrant_prefix": "example",
                "blob_config": {
                    "provider": "minio",
                    "bucket": "example-bucket",
                    "prefix": "example_"
                },
                "model_config": {
                    "llm": "openai",
                    "embeddings": "openai-embedding",
                    "nli": "nli-model"
                },
                "tool_config": {
                    "sql": True,
                    "calculator": True,
                    "tavily": False
                }
            },
            ]
        },
    }

class TenantUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: Optional[str] = None
    qdrant_prefix: Optional[str] = None
    blob_config: Optional[Dict[str, Any]] = None
    model_cfg: Optional[Dict[str, Any]] = Field(default=None, validation_alias='model_config')
    tool_config: Optional[Dict[str, Any]] = None

class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: uuid.UUID
    name: str
    tenant_db_url: str
    qdrant_prefix: str
    blob_config: Dict[str, Any]
    # Map ORM attr `model_config` to output key `model_config`
    model_cfg: Dict[str, Any] = Field(serialization_alias='model_config', validation_alias='model_config')
    tool_config: Dict[str, Any]
