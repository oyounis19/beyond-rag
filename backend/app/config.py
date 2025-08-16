from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database / Caches
    database_url: str = "postgresql+psycopg://postgres:postgres@postgres:5432/beyondrag"
    redis_auth: str = ""
    redis_url: str = "redis://:myredissecret@redis:6379/0"
    qdrant_url: str = "http://qdrant:6333"

    # Object storage (MinIO)
    minio_endpoint: str = "http://minio:9090"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "beyondrag"

    # API keys
    google_api_key: str = ""
    openai_api_key: str = ""
    groq_api_key: str = ""

    # Models
    embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    nli_model: str = "cross-encoder/nli-deberta-v3-large"
    conflict_llm_model: str = "llama-3.1-8b-instant"
    gemini_llm_model: dict = {
        "name": "gemini-2.5-flash",
        "temperature": 0.3,
        "max_tokens": 1024
    }
    openai_llm_model: dict = {
        "name": "gpt-4o",
        "temperature": 0.3,
        "max_tokens": 1024
    }

    # Retrieval / Conflicts
    top_k_neighbors: int = 3
    contradiction_score_threshold: float = 0.85
    dedup_similarity_threshold: float = 0.97

    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 50

    # Tools
    tavily_api_key: str = ""

    # Langfuse
    langfuse_host: str = "http://langfuse-web:3000"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    class Config:
        env_file = ".env"
        env_prefix = ""

settings = Settings()
