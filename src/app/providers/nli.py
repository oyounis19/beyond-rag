import logging
from sentence_transformers import CrossEncoder

from ..config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NLIProvider:
    def __init__(self):
        logger.info(f"Initializing NLIProvider with model: {settings.nli_model}")
        self.model = CrossEncoder(settings.nli_model)

    def predict(self, sentence_pairs: list[tuple[str, str]]) -> list[float]:
        return self.model.predict(sentence_pairs)
        