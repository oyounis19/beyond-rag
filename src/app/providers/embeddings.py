import logging
from sentence_transformers import SentenceTransformer

from ..config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmbeddingsProvider:
    def __init__(self):
        logger.info(f"Initializing EmbeddingsProvider with model: {settings.embed_model}")
        self.model = SentenceTransformer(settings.embed_model)

    def embed_text(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()
