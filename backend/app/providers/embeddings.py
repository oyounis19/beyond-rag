from sentence_transformers import SentenceTransformer
from ..config import settings

class EmbeddingsProvider:
    def __init__(self):
        print(f"Initializing EmbeddingsProvider with model: {settings.embed_model}")
        self.model = SentenceTransformer(settings.embed_model)

    def embed_text(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()
