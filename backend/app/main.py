from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .api.ingestion import router as ingestion_router
from .api.conflicts import router as conflicts_router
from .api.chat import router as chat_router
from .api.evals import router as evals_router

app = FastAPI(title="BeyondRAG API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion_router)
app.include_router(conflicts_router)
app.include_router(chat_router)
app.include_router(evals_router)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "qdrant_url": settings.qdrant_url,
        "redis_url": settings.redis_url,
        "database_url": settings.database_url,
    }
