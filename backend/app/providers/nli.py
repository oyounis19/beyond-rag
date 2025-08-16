from sentence_transformers import CrossEncoder
from ..config import settings

class NLIProvider:
    def __init__(self):
        print(f"Initializing NLIProvider with model: {settings.nli_model}")
        self.model = CrossEncoder(settings.nli_model)

    def predict(self, sentence_pairs: list[tuple[str, str]]) -> list[float]:
        return self.model.predict(sentence_pairs)
        