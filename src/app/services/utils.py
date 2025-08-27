import torch
import os, re, io
import asyncio
import tempfile
import tiktoken
import logging
import pandas as pd
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from langchain_docling.loader import ExportType
from langchain_community.document_loaders import RecursiveUrlLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_docling import DoclingLoader

from ..providers.embeddings import EmbeddingsProvider
from ..providers.llm import LLMProvider
from ..providers.nli import NLIProvider
from ..models.app_models import Chunk
from ..config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def parse_url(url: str) -> bytes:
    """
    Fetch content from a URL and return it as bytes.
    """
    def bs4_extractor(html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        return re.sub(r"\n\n+", "\n\n", soup.text).strip()

    loader = RecursiveUrlLoader(
        url=url,
        max_depth=1,
        extractor=bs4_extractor,
        timeout=10,
    )
    docs = loader.load()
    if not docs:
        raise ValueError(f"Failed to fetch content from URL: {url}")
    return docs[0].page_content.encode('utf-8')

def excel_parse(content: bytes) -> str:
    df = pd.read_excel(io.BytesIO(content))

    # Drop completely empty rows/cols
    df.dropna(how="all", inplace=True)
    df.dropna(axis=1, how="all", inplace=True)

    # Round numeric columns to save tokens
    for col in df.select_dtypes(include="number"):
        df[col] = df[col].round(2)

    # Compact TSV format
    return df.to_csv(index=False, sep="\t", na_rep="")

def csv_parse(content: bytes) -> str:
    df = pd.read_csv(io.BytesIO(content), sep=None, engine='python')

    # Drop completely empty rows/cols
    df.dropna(how="all", inplace=True)
    df.dropna(axis=1, how="all", inplace=True)

    # Round numeric columns to save tokens
    for col in df.select_dtypes(include="number"):
        df[col] = df[col].round(2)

    # Compact TSV format
    return df.to_csv(index=False, sep="\t", na_rep="")

def pdf_parse(content: bytes, docling: bool = False) -> str:
    def clean_spaces(text: str) -> str:
        text = re.sub(r"\n{3,}", "\n\n", text)

        cleaned_lines = []
        for line in text.splitlines():
            if not line.strip():
                cleaned_lines.append("")
            else:
                cleaned_lines.append(re.sub(r"[ \t]{2,}", " ", line.strip()))
        merged = re.sub(r"(?<![.!?])\n(?!\n)", " ", "\n".join(cleaned_lines))
        return merged.strip()

    if not docling:
        reader = PdfReader(io.BytesIO(content))
        text = [
            (page.extract_text() or "").strip()
            for page in reader.pages
        ]
        return clean_spaces("\n".join(text))
    
    tmp_path = None
    try:
        # Write bytes to a temporary file so Docling can read it
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        loader = DoclingLoader(file_path=tmp_path, export_type=ExportType.MARKDOWN)
        docs = loader.load()

        if not docs:
            raise ValueError("Failed to parse PDF content with Docling")

        return clean_spaces(docs[0].page_content)
    except Exception as e:
        raise ValueError(f"Error parsing PDF content: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

def chunk_text(text: str) -> list[dict]:
    """
    Simple text chunking function that splits text into smaller chunks.
    """
    if not text:
        return []
    
    def tiktoken_len(text):
        tokenizer = tiktoken.get_encoding("cl100k_base")
        tokens = tokenizer.encode(text)
        return len(tokens)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        length_function=tiktoken_len,
    )
    chunks = splitter.split_text(text)

    return [{
            "text": chunk,
            "page": None,  # Placeholder, can be set later if needed
            "section_path": None,  # Placeholder, can be set later if needed
            "hash": tiktoken_len(chunk),  # Use token length as a simple hash
        } for chunk in chunks]

def embed_chunks(chunks: list[str], embedder: EmbeddingsProvider) -> list[list[float]]:
    if not chunks:
        return []
    return [embedder.embed_text(chunk) for chunk in chunks]

async def check_conflicts(chunk: Chunk, similar_chunks: list, nli_model: NLIProvider, llm: LLMProvider, semaphore: asyncio.Semaphore) -> dict:
    """
    Check for duplicates and contradictions in the given chunk against similar chunks.
    
    Steps:
        - Step 1: Use NLI model for a fast check.
        - Step 2: Escalate to LLM for ambiguous cases.
        - Step 3: Return structured results as well as any LLM tasks for further processing.
    """
    duplicates = []
    contradictions = []

    # NLI Batch Prediction
    if not similar_chunks:
        return {"duplicates": [], "contradictions": []}, []

    sentence_pairs = [(chunk.text, similar.payload['text']) for similar in similar_chunks]
    logger.info(f"Batch NLI prediction for {len(sentence_pairs)} pairs")
    nli_logits = nli_model.predict(sentence_pairs)
    nli_scores = torch.nn.functional.softmax(torch.tensor(nli_logits, device=device), dim=1)

    llm_escalation_tasks = []
    for i, similar_chunk in enumerate(similar_chunks):
        score_for_pair = nli_scores[i]
        nli_label = ['contradiction', 'entailment', 'neutral'][score_for_pair.argmax()]
        nli_confidence = score_for_pair.max()

        conflict_payload = {
            "chunk_id": str(chunk.id),
            "chunk_text": chunk.text,
            "conflicting_chunk_id": str(similar_chunk.id),
            "conflicting_chunk_text": similar_chunk.payload['text'],
            "conflicting_document_id": similar_chunk.payload['document_id']
        }
        
        # High-confidence NLI results
        if nli_label == 'entailment' and nli_confidence > settings.dedup_similarity_threshold:
            duplicates.append({**conflict_payload, "judged_by": "nli", "score": float(nli_confidence)})
            continue
        if nli_label == 'contradiction' and nli_confidence > settings.contradiction_score_threshold:
            contradictions.append({**conflict_payload, "judged_by": "nli", "score": float(nli_confidence)})
            continue
        if nli_label == 'neutral' and nli_confidence > settings.neutral_score_threshold:
            logger.info("Neutral")
            continue

        # Escalate ambiguous cases to LLM
        logger.info(f"Ambiguous ({nli_label}, Conf: {nli_confidence:.2f}). Escalating to LLM.")
        task = llm.predict_conflict(
            llm=llm.conflict_llm,
            chunk1=chunk.text,
            chunk2=similar_chunk.payload['text'],
            semaphore=semaphore,
            conflict_payload=conflict_payload
        )
        llm_escalation_tasks.append(task)
        
    return {"duplicates": duplicates, "contradictions": contradictions}, llm_escalation_tasks
