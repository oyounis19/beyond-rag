import uuid
import asyncio
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException
from ..providers.app_context import AppContext
from ..providers.storage import StorageProvider
from ..models.app_models import Document, Chunk
from xxhash import xxh64
import io
import logging
from datetime import datetime, timezone
from .utils import *
from ..providers.qdrant_client import QdrantProvider
from qdrant_client.models import Filter, FieldCondition, MatchValue
from ..providers.embeddings import EmbeddingsProvider
from ..providers.llm import LLMProvider
from ..providers.nli import NLIProvider

# Configure logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ALLOWED_EXT = ["txt",
    "md",
    "pdf",
    "xlsx",
    "xls",
]

MAX_FILE_BYTES = 10 * 1024 * 1024

class IngestionService:
    def __init__(self):
        self.control_db = None
        self.ctx = None
        self.storage = StorageProvider()
        self.qdrant = QdrantProvider()
        self.llm = LLMProvider()
        self.nli_model = NLIProvider()
        self.embed_model = EmbeddingsProvider()

    def init_tenant(self, context: AppContext, db: Session):
        self.control_db = db
        self.ctx = context

    def _store_raw_file(self, *, content: bytes, filename: str, external_ref: str | None) -> str:
        object_name = f"raw/{filename}".lstrip('/')
        self.storage.ensure_bucket(self.ctx.bucket)
        if not content: # URL
            content = parse_url(external_ref)
            filename += ".txt"
        self.storage.client.put_object(self.ctx.bucket, object_name, io.BytesIO(content), length=len(content))
        return object_name

    def _parse_document(self, *, storage_key: str, extension: str, docling: bool) -> str:
        """
        Parse the document based on extension.
        - PDF -> Docling
        - Text/Markdown/URL -> simple text parsing
        - Excel -> Convert to CSV(pandas) and parse CSV
        - CSV -> CSV parsing
        """
        # Get the document content from storage
        content = self.storage.client.get_object(self.ctx.bucket, storage_key).read()
        if extension == "pdf":
            # Use PDF parsing pipeline
            return pdf_parse(content, docling=docling)
        elif extension in ["txt", "md"]:
            # Simple text parsing
            return content.decode()
        elif extension in ["xlsx", "xls"]:
            return excel_parse(content)
        elif extension == "csv":
            return csv_parse(content)
        
        return ""

    def _chunk_document(self, *, document_id: uuid.UUID, text: str) -> int:
        s = self.ctx.get_db_session()
        try:
            existing = s.query(Chunk).filter(Chunk.document_id == document_id).count()
            if existing > 0:
                # Already chunked, return existing count
                return existing
            
            chunks = chunk_text(text)
            if not chunks:
                return 0
            
            chunk_objects = [
                Chunk(document_id=document_id, idx=i, text=chunk["text"], hash=xxh64(chunk["text"].encode()).hexdigest(), page=chunk.get("page"), section_path=chunk.get("section_path"))
                for i, chunk in enumerate(chunks)
            ]
            s.bulk_save_objects(chunk_objects)
            s.commit()
            return len(chunk_objects)
        except Exception as e:
            s.rollback()
            raise HTTPException(status_code=500, detail=f"Error chunking document: {str(e)}")
        finally:
            self.ctx.close_session(s)

    def _embed_document_chunks(self, *, document_id: uuid.UUID) -> int:
        s = self.ctx.get_db_session()
        try:
            chunks = s.query(Chunk).filter(Chunk.document_id == document_id)
            if not chunks.count():
                raise HTTPException(status_code=404, detail="No chunks found for document")
            embed_vectors = embed_chunks([chunk.text for chunk in chunks], embedder=self.embed_model)
            # Store embeddings in qdrant
            self.qdrant.ensure_collection(self.ctx.qdrant_collection, dim=384)
            for chunk, vector in zip(chunks, embed_vectors):
                self.qdrant.client.upsert(
                    collection_name=self.ctx.qdrant_collection,
                    points=[{
                        "id": str(chunk.id),
                        "vector": vector,
                        "payload": {
                            "text": chunk.text,
                            "document_id": str(document_id),
                            "idx": chunk.idx,
                        }
                    }]
                )
            s.commit()
            return len(embed_vectors)
        except Exception as e:
            s.rollback()
            raise HTTPException(status_code=500, detail=f"Error embedding document chunks: {str(e)}")
        finally:
            self.ctx.close_session(s)

    async def _detect_conflicts(self, *, document_id: uuid.UUID) -> dict:
        """
        Detect duplicates and contradictions using NLI model
        Steps:
        1. Get 10 semantically similar chunks from Qdrant for each chunk in the document.
        2. Do NLI inference to find duplicates and contradictions.
        3. If NLI scores are below a threshold, use LLM to analyze text for contradictions.
        """
        s = self.ctx.get_db_session()
        try:
            # Get all chunks for the document
            chunks = s.query(Chunk).filter(Chunk.document_id == document_id).all()
            if not chunks:
                return {"duplicates": [], "contradictions": []}

            logger.info(f"Detecting conflicts for document: {document_id} with {len(chunks)} chunks")

            all_conflicts = {"duplicates": [], "contradictions": []}
            all_llm_tasks = []
            for chunk in chunks:
                # Get the embedding vector for the chunk from qdrant
                get_chunk_vector = lambda chunk_id: self.qdrant.client.retrieve(
                    collection_name=self.ctx.qdrant_collection,
                    ids=[str(chunk_id)],
                    with_vectors=True,
                )[0].vector

                # Get 10 similar chunks for each chunk in the document from Qdrant
                similar_chunks = self.qdrant.client.search(
                    collection_name=self.ctx.qdrant_collection,
                    query_vector=get_chunk_vector(chunk.id),
                    limit=10,
                    query_filter=Filter( # Search in all document chunks except the current one
                        must_not=[
                            FieldCondition(
                                key="document_id",
                                match={"value": str(document_id)}
                            )
                        ]
                    ),
                    with_payload=True,
                )

                logger.info(f"Found {len(similar_chunks) if similar_chunks else 0} similar chunks for chunk {chunk.id}")
                
                semaphore = asyncio.Semaphore(5)  # Up to 5 concurrent LLM calls
                
                # Check for duplicates/contradictions
                conflicts, llm_tasks = await check_conflicts(chunk, similar_chunks, nli_model=self.nli_model, llm=self.llm, semaphore=semaphore)

                all_llm_tasks.extend(llm_tasks)
                
                # Full Parallelism: Remove these 2 lines
                all_conflicts["duplicates"].extend(conflicts["duplicates"])
                all_conflicts["contradictions"].extend(conflicts["contradictions"])

            logger.info(f"LLM tasks to execute: {len(all_llm_tasks)}")
            results = await asyncio.gather(*all_llm_tasks)
            for result in results:
                if not result: continue
                if result['label'].lower() == 'entailment':
                    all_conflicts["duplicates"].append(result['payload'])
                elif result['label'].lower() == 'contradiction':
                    all_conflicts["contradictions"].append(result['payload'])
                        
            logger.info(f"All conflicts detected: {all_conflicts}")
            
            # Store conflicts in database
            self._store_conflicts(all_conflicts, s)
            
            return all_conflicts
        finally:
            self.ctx.close_session(s)

    async def publish_document_stream(self, document_id: uuid.UUID, *, docling: bool = False):
        """Stream publishing progress with real-time updates"""
        import time
        from tqdm import tqdm
        from datetime import datetime, timezone
        
        s = self.ctx.get_db_session()
        try:
            doc = s.query(Document).filter(Document.id == document_id).first()
            if not doc:
                yield {"stage": "error", "error": "Document not found", "ok": False}
                return
            if doc.status == "published":
                yield {"stage": "complete", "ok": True, "document_id": str(doc.id), "already_published": True}
                return

            # Stage 1: Parse
            yield {"stage": "parsing", "message": f"Parsing document with {'Docling' if docling else 'PyPDF2'}...", "progress": 0}
            start_time = time.time()
            
            logger.info(f"Parsing document: {doc.id} with extension: {doc.extension}, Storage key: {doc.storage_key}")
            parsed_text = self._parse_document(storage_key=doc.storage_key, extension=doc.extension, docling=docling)
            
            parse_time = time.time() - start_time
            yield {"stage": "parsed", "message": f"Document parsed in {parse_time:.2f}s", "progress": 20, "text_length": len(parsed_text)}

            # Stage 2: Chunk
            yield {"stage": "chunking", "message": "Splitting document into 200-token chunks...", "progress": 20}
            start_time = time.time()
            
            logger.info(f"Chunking document: {doc.id} with parsed text length: {len(parsed_text)}")
            created_chunks = self._chunk_document(text=parsed_text, document_id=document_id)
            
            chunk_time = time.time() - start_time
            yield {"stage": "chunked", "message": f"Created {created_chunks} chunks in {chunk_time:.2f}s", "progress": 40, "chunks_created": created_chunks}

            # Stage 3: Embed
            yield {"stage": "embedding", "message": f"Generating embeddings for {created_chunks} chunks...", "progress": 40}
            start_time = time.time()
            
            logger.info(f"Embedding document chunks for: {doc.id}, Chunk count: {created_chunks}")
            embedded = self._embed_document_chunks(document_id=document_id)
            
            embed_time = time.time() - start_time
            yield {"stage": "embedded", "message": f"Generated embeddings in {embed_time:.2f}s", "progress": 70, "chunks_embedded": embedded}

            # Stage 4: Analyze conflicts with progress
            yield {"stage": "analyzing", "message": "Analyzing conflicts with existing content...", "progress": 70}
            start_time = time.time()
            
            # Get chunks for progress tracking
            chunks = s.query(Chunk).filter(Chunk.document_id == document_id).all()
            chunk_count = len(chunks)
            
            logger.info(f"Analyzing conflicts for document: {doc.id} with {chunk_count} chunks")
            
            # Provide realistic progress updates during conflict detection
            yield {
                "stage": "analyzing",
                "message": f"Analyzing {chunk_count} chunks for conflicts...",
                "progress": 75,
                "chunks_processed": 0,
                "total_chunks": chunk_count
            }
            
            # Call the real conflict detection
            conflicts = await self._detect_conflicts(document_id=document_id)
            conflict_time = time.time() - start_time
            
            logger.info(f"Conflicts found: {conflicts}")
            has_conflicts = bool(conflicts.get("duplicates") or conflicts.get("contradictions"))
            
            # Report final analysis completion
            yield {
                "stage": "analyzed",
                "message": f"Conflict analysis completed in {conflict_time:.2f}s",
                "progress": 90,
                "chunks_processed": chunk_count,
                "total_chunks": chunk_count,
                "duplicates_count": len(conflicts.get("duplicates", [])),
                "contradictions_count": len(conflicts.get("contradictions", []))
            }
            
            if has_conflicts:
                # Set status to pending_review when conflicts are found
                doc.status = "pending_review"
                s.commit()
                yield {
                    "stage": "conflicts_detected",
                    "message": f"Conflicts detected - requires review",
                    "progress": 95,
                    "ok": True,
                    "requires_review": True,
                    "document_id": str(doc.id),
                    "conflicts": conflicts,
                    "duplicates_count": len(conflicts.get("duplicates", [])),
                    "contradictions_count": len(conflicts.get("contradictions", []))
                }
                return

            # Stage 5: Publish (no conflicts)
            yield {"stage": "publishing", "message": "Finalizing publication...", "progress": 90}
            doc.status = "published"
            doc.effective_at = datetime.now(timezone.utc)
            s.commit()
            
            yield {
                "stage": "complete",
                "message": "Document published successfully!",
                "progress": 100,
                "ok": True,
                "document_id": str(doc.id),
                "published": True
            }
            
        finally:
            self.ctx.close_session(s)

    def _store_conflicts(self, conflicts: dict, session):
        """Store detected conflicts in the database"""
        from ..models.app_models import Conflict
        
        # Store contradictions
        for contradiction in conflicts.get("contradictions", []):
            # Map the field names from conflict detection to database schema
            new_chunk_id = contradiction.get("chunk_id")
            existing_chunk_id = contradiction.get("conflicting_chunk_id")
            
            if not new_chunk_id or not existing_chunk_id:
                logger.warning(f"Skipping contradiction with missing IDs: {contradiction}")
                continue
                
            existing_conflict = session.query(Conflict).filter(
                Conflict.new_chunk_id == new_chunk_id,
                Conflict.existing_chunk_id == existing_chunk_id
            ).first()
            
            if not existing_conflict:
                conflict_record = Conflict(
                    new_chunk_id=new_chunk_id,
                    existing_chunk_id=existing_chunk_id,
                    label="contradiction",
                    score=contradiction.get("score", 0.0),
                    neighbor_sim=contradiction.get("neighbor_sim"),
                    resolution_action=None
                )
                session.add(conflict_record)
        
        # Store duplicates as contradictions with different label
        for duplicate in conflicts.get("duplicates", []):
            # Map the field names from conflict detection to database schema
            new_chunk_id = duplicate.get("chunk_id")
            existing_chunk_id = duplicate.get("conflicting_chunk_id")
            
            if not new_chunk_id or not existing_chunk_id:
                logger.warning(f"Skipping duplicate with missing IDs: {duplicate}")
                continue
                
            existing_conflict = session.query(Conflict).filter(
                Conflict.new_chunk_id == new_chunk_id,
                Conflict.existing_chunk_id == existing_chunk_id
            ).first()
            
            if not existing_conflict:
                conflict_record = Conflict(
                    new_chunk_id=new_chunk_id,
                    existing_chunk_id=existing_chunk_id,
                    label="duplicate",
                    score=duplicate.get("score", 0.0),
                    neighbor_sim=duplicate.get("neighbor_sim"),
                    resolution_action=None
                )
                session.add(conflict_record)
        
        session.commit()

    def _check_and_publish_if_ready(self, document_id: uuid.UUID, session):
        """Check if document has any unresolved conflicts and publish if ready"""
        from ..models.app_models import Conflict, Document
        from datetime import datetime, timezone
        
        # Get the document
        doc = session.query(Document).filter(Document.id == document_id).first()
        if not doc or doc.status != "pending_review":
            return False
            
        # Check if there are any unresolved conflicts for chunks of this document
        unresolved_conflicts = session.query(Conflict).join(
            Chunk, Conflict.new_chunk_id == Chunk.id
        ).filter(
            Chunk.document_id == document_id,
            Conflict.resolved_at.is_(None)
        ).count()
        
        if unresolved_conflicts == 0:
            # No unresolved conflicts, publish the document
            doc.status = "published"
            doc.effective_at = datetime.now(timezone.utc)
            session.commit()
            logger.info(f"Document {document_id} published after conflict resolution")
            return True
            
        return False

    def _validate_file(self, file: UploadFile | str) -> str:
        """Validate file extension and size.
        Returns a hash of the file content for deduplication."""
        if isinstance(file, str):
            # Check if the URL is valid
            if not file.startswith("http://") and not file.startswith("https://"):
                raise HTTPException(status_code=400, detail=f"Invalid URL: {file}")
            # If valid, return a hash of the URL for deduplication
            return xxh64(file.encode()).hexdigest(), None

        ext = file.filename.split('.')[-1] or "txt"
        if ext.lower() not in ALLOWED_EXT:
            raise HTTPException(status_code=415, detail=f"Unsupported file extension: {ext}")
        content = file.file.read()
        if len(content) > MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail=f"File exceeds max size {MAX_FILE_BYTES} bytes")
        file_hash = xxh64(content).hexdigest()
        return file_hash, content

    def ingest(self, file: UploadFile | str, title: str | None = None):
        """
        Upload a file/URL.
        
        Steps:
        1. Validate Extension and size.
        2. Check for existing document with same name or hash.
        3. Store raw file in object storage.
        4. Create a draft document record in the tenant database.
        5. Return document ID and status.
        """
        # Step 1: Validate Extension & size
        file_hash, content = self._validate_file(file)

        s = self.ctx.get_db_session()
        duplicate = False
        
        try:
            external_ref = file.filename if content else file
            extension = file.filename.split('.')[-1] if content else 'txt'
            existing_doc = s.query(Document).filter(Document.external_ref == external_ref).first()
            if existing_doc:
                # Step 1b: Duplicate (exact) short-circuit based on hash vs current file_hash
                if existing_doc.file_hash == file_hash:
                    return {
                        "document_id": str(existing_doc.id),
                        "duplicate": True,
                        "status": existing_doc.status,
                        "processing_status": "duplicate",
                    }
                duplicate = True

            title = title or external_ref

            # Step 2: Persist raw file (object storage)
            storage_key = self._store_raw_file(content=content, filename=f"{title}_{file_hash[:4]}.{extension}", external_ref=external_ref)
            doc = Document(
                title=title,
                external_ref=external_ref,
                file_hash=file_hash,
                storage_key=storage_key,
                extension=extension,
                status="draft"
            )
            s.add(doc)
            s.flush()

            s.commit()
            return {
                "document_id": str(doc.id),
                "duplicate": duplicate,
                "status": doc.status,
                "processing_status": "uploaded",
            }
        finally:
            self.ctx.close_session(s)

    async def publish(self, document_id: uuid.UUID, docling: bool = False):
        """
        Publish a document.
        
        Steps:
        1. Ensure document exists and is not already published.
        2. Parse the document, using appropriate tools based on extension.
        3. Chunk the document, using langchain recursive text splitter.
        4. Embed the document, using embedding model.
        5. Analyze duplicates and contradictions.
        6. Publish the document if no conflicts are found.
        """
        s = self.ctx.get_db_session()
        try:
            doc = s.query(Document).filter(Document.id == document_id).first()
            if not doc:
                return {"ok": False, "error": "not_found"}
            if doc.status == "published":
                return {"ok": True, "document_id": str(doc.id), "already_published": True}

            # Stage 1: Parse
            logger.info(f"Parsing document: {doc.id} with extension: {doc.extension}, Storage key: {doc.storage_key}")
            parsed_text = self._parse_document(storage_key=doc.storage_key, extension=doc.extension, docling=docling)

            # Stage 2: Chunk
            logger.info(f"Chunking document: {doc.id} with parsed text length: {len(parsed_text)}")
            created_chunks = self._chunk_document(text=parsed_text, document_id=document_id)

            # Stage 3: Embed
            logger.info(f"Embedding document chunks for: {doc.id}, Chunk count: {created_chunks}")
            embedded = self._embed_document_chunks(document_id=document_id)

            # Stage 4: Analyze duplicates & contradictions
            logger.info(f"Analyzing conflicts for document: {doc.id}, Embedded chunks: {embedded}")
            conflicts = await self._detect_conflicts(document_id=document_id)
            logger.info(f"Conflicts found: {conflicts}")
            has_conflicts = bool(conflicts.get("duplicates") or conflicts.get("contradictions"))
            if has_conflicts:
                # Set status to pending_review when conflicts are found
                doc.status = "pending_review"
                s.commit()
                return {
                    "ok": True,  # Changed to True since the operation succeeded
                    "requires_review": True,
                    "document_id": str(doc.id),
                    "conflicts": conflicts,
                    "stage": "analyzed",
                }

            # Stage 5: Publish (no conflicts)
            doc.status = "published"
            doc.effective_at = datetime.now(timezone.utc)
            s.commit()
            return {
                "ok": True,
                "document_id": str(doc.id),
                "published": True,
                "chunks": created_chunks,
                "embedded": embedded,
            }
        finally:
            self.ctx.close_session(s)

    def document_status(self, document_id: uuid.UUID):
        s = self.ctx.get_db_session()
        try:
            doc = s.query(Document).filter(Document.id == document_id).first()
            if not doc:
                return None
            chunk_count = s.query(Chunk).filter(Chunk.document_id == document_id).count()
            return {
                "document": {
                    "id": str(doc.id),
                    "name": doc.title,
                    "status": doc.status,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "file_hash": doc.file_hash,
                    "effective_at": doc.effective_at.isoformat() if doc.effective_at else None,
                },
                "total_chunks": chunk_count,
                "total_conflicts": 0,
                "total_dedup_groups": 0,
            }
        finally:
            self.ctx.close_session(s)

    def list_documents(self):
        logger.info("Listing documents for tenant")
        s = self.ctx.get_db_session()
        try:
            docs = s.query(Document).order_by(Document.created_at.desc()).all()
            logger.info(f"Found documents: {len(docs)}")
            out = []
            for d in docs:
                logger.debug(f"Document {d.id} status: {d.status}")
                out.append({
                    "id": str(d.id),
                    "name": d.title,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                    "status": d.status,
                })
            return out
        finally:
            self.ctx.close_session(s)

    def get_document_chunks(self, document_id: uuid.UUID):
        """
        Get all chunks for a document.
        """
        s = self.ctx.get_db_session()
        try:
            doc = s.query(Document).filter(Document.id == document_id).first()
            if not doc:
                return None
            
            logger.info(f"Getting chunks for document: {doc.id} - {doc.title}")
            
            rows = (
                s.query(Chunk)
                .filter(Chunk.document_id == document_id)
                .order_by(Chunk.idx.asc())
                .all()
            )
            return [
                {
                    "id": str(c.id),
                    "idx": c.idx,
                    "text_preview": c.text[:160],
                    "hash": c.hash,
                    "page": c.page,
                    "section_path": c.section_path,
                }
                for c in rows
            ]
        finally:
            self.ctx.close_session(s)
    def delete_document(self, document_id: uuid.UUID):
        """
        Delete a document and all its associated data.
        
        Steps:
        1. Get document from database
        2. Delete chunks from database
        3. Delete embeddings from Qdrant
        4. Delete file from MinIO storage
        5. Delete document record
        """
        s = self.ctx.get_db_session()
        try:
            doc = s.query(Document).filter(Document.id == document_id).first()
            if not doc:
                return False
            
            logger.info(f"Deleting document: {doc.id} - {doc.title}")
            
            # Delete chunks from database
            chunk_count = s.query(Chunk).filter(Chunk.document_id == document_id).count()
            if chunk_count > 0:
                logger.info(f"Deleting {chunk_count} chunks from database")
            
            # Delete embeddings from Qdrant (if they exist)
            try:
                if chunk_count > 0:
                    # Get all chunk IDs to delete from Qdrant
                    chunk_ids = [str(chunk.id) for chunk in s.query(Chunk.id).filter(Chunk.document_id == document_id).all()]
                    if chunk_ids:
                        logger.info(f"Deleting {len(chunk_ids)} embeddings from Qdrant")
                        self.qdrant.client.delete(
                            collection_name=self.ctx.qdrant_collection,
                            points_selector=chunk_ids
                        )
                s.query(Chunk).filter(Chunk.document_id == document_id).delete()
            except Exception as e:
                logger.warning(f"Failed to delete embeddings from Qdrant: {e}")
            
            # Delete file from MinIO storage
            try:
                if doc.storage_key:
                    logger.info(f"Deleting file from storage: {doc.storage_key}")
                    self.storage.client.remove_object(self.ctx.bucket, doc.storage_key)
            except Exception as e:
                logger.warning(f"Failed to delete file from storage: {e}")
            
            # Delete document record
            s.delete(doc)
            s.commit()
            
            logger.info(f"Successfully deleted document: {document_id}")
            return True
            
        except Exception as e:
            s.rollback()
            logger.error(f"Error deleting document {document_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")
        finally:
            self.ctx.close_session(s)

    def list_conflicts(self):
        return []

    def list_chunks(self, document_id: uuid.UUID):
        s = self.ctx.get_db_session()
        try:
            rows = (
                s.query(Chunk)
                .filter(Chunk.document_id == document_id)
                .order_by(Chunk.idx.asc())
                .all()
            )
            return [
                {
                    "id": str(c.id),
                    "idx": c.idx,
                    "text_preview": c.text[:160],
                    "hash": c.hash,
                }
                for c in rows
            ]
        finally:
            self.ctx.close_session(s)
