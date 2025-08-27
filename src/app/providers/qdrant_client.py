import logging

from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

from ..config import settings
from ..providers.embeddings import EmbeddingsProvider

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QdrantProvider:
    def __init__(self):
        logger.info(f"Initializing QdrantProvider with URL: {settings.qdrant_url}")
        self.client = QdrantClient(url=settings.qdrant_url)
        self.async_client = AsyncQdrantClient(url=settings.qdrant_url)

    def ensure_collection(self, name: str, dim: int = 384):
        if name not in [c.name for c in self.client.get_collections().collections]:
            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    def drop_collection(self, name: str):
        try:
            self.client.delete_collection(collection_name=name)
        except Exception:
            pass
    
    def get_relevant_chunks(self, content: str, top_k: int = 5) -> list:
        """
        Retrieve relevant chunks from Qdrant based on the query.
        """
        embedder = EmbeddingsProvider()
        query_vector = embedder.embed_text(content)
        return self.client.search(
            collection_name="chunks",
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
        )