import json
import asyncio
from sqlalchemy.orm import Session
from json_repair import repair_json

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMRouterChain, MultiPromptChain

from langfuse import Langfuse, get_client
from langfuse.langchain import CallbackHandler
from ..config import settings
from ..models.app_models import Document
from .prompts import conflict_sys_prompt
from .qdrant_client import QdrantProvider
from ..providers.app_context import AppContext
from . import prompts
class LLMProvider:

    available_providers = ["gemini", "vllm", "openai"]

    def __init__(self):
        print("Initializing LLMProvider...")
        self.langfuse = Langfuse(
            host=settings.langfuse_host,
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key
        )
        # self.client = get_client(
        #     public_key=settings.langfuse_public_key,
        # )
        self.conflict_llm = ChatGroq(
            temperature=0.0,
            model=settings.conflict_llm_model,
            max_tokens=512,
            api_key=settings.groq_api_key,
            callbacks=[CallbackHandler(public_key=settings.langfuse_public_key)]
        )
        self.gemini_llm = ChatGoogleGenerativeAI(
            temperature=settings.gemini_llm_model["temperature"],
            model=settings.gemini_llm_model["name"],
            max_tokens=settings.gemini_llm_model["max_tokens"],
            api_key=settings.google_api_key,
            callbacks=[CallbackHandler(public_key=settings.langfuse_public_key)]
        )
        self.openai_llm = ChatOpenAI(
            temperature=settings.openai_llm_model["temperature"],
            model=settings.openai_llm_model["name"],
            max_tokens=settings.openai_llm_model["max_tokens"],
            api_key=settings.openai_api_key,
            callbacks=[CallbackHandler(public_key=settings.langfuse_public_key)]
        )
        self.qdrant_client = QdrantProvider()
        self.ctx = None


    def init_tenant(self, context: AppContext, db: Session):
        self.control_db = db
        self.ctx = context

    def _route(self, query: str) -> str:
        """Decide if query needs RAG or not."""
        resp = self.conflict_llm.invoke([("system", prompts.router_prompt.format(query=query))])
        return resp.content.strip().lower()
    
    async def predict_conflict(self, llm: ChatGroq, chunk1: str, chunk2: str, semaphore: asyncio.Semaphore, conflict_payload: dict) -> dict:
        """
        Wrapper for the LLM call to format the output.
        """
        messages = [
            ("system", conflict_sys_prompt),
            ("human", f"Chunk 1: \"{chunk1}\"\n\nChunk 2: \"{chunk2}\"")
        ]
        client = get_client(
            public_key=settings.langfuse_public_key,
        )
        async with semaphore:
            try:
                response = await llm.ainvoke(messages)
                
                if not response.content:
                    return {}

                output = response.content.strip()
                output_json = json.loads(repair_json(output))

                return {
                    "label": output_json["label"],
                    "payload": {
                        **conflict_payload,
                        "judged_by": "llm",
                        "reasoning": output_json["reasoning"]
                    }
                }
            except Exception as e:
                print(f"LLM prediction error: {e}")
                return {}
            finally:
                client.flush()

    def generate_gemini(self, messages: list) -> str:
        """
        Generate a response using the Gemini LLM.
        """
        client = get_client(
            public_key=settings.langfuse_public_key,
        )
        try:
            response = self.gemini_llm.invoke(messages)
            return response.content.strip()
        except Exception as e:
            print(f"Gemini LLM error: {e}")
            return ""
        finally:
            client.flush()
        
    def generate_openai(self, messages: list) -> str:
        """
        Generate a response using the OpenAI LLM.
        """
        client = get_client(
            public_key=settings.langfuse_public_key,
        )
        try:
            response = self.openai_llm.invoke(messages)
            return response.content.strip()
        except Exception as e:
            print(f"OpenAI LLM error: {e}")
            return ""
        finally:
            client.flush()
    
    def generate_response(self, content: str, provider: str, session_id: str = None) -> tuple[str, list]:
        """
        Generate response (RAG or direct) using specified provider with chat history.
        """
        s = self.ctx.get_db_session()
        chunks = []  # Initialize chunks

        # Get chat history for context
        chat_history = []
        if session_id:
            from ..models.app_models import ChatMessage
            recent_messages = s.query(ChatMessage)\
                .filter(ChatMessage.session_id == session_id)\
                .order_by(ChatMessage.created_at.asc())\
                .all()
            
            # Add all previous messages in order
            for msg in recent_messages:
                if msg.role == "user":
                    chat_history.append(("human", msg.content))
                elif msg.role == "assistant":
                    chat_history.append(("assistant", msg.content))

        # 1) Routing Decision
        route = self._route(content)
        print(f"Router decision: {route}")

        messages = [("system", prompts.main_sys_prompt)]
        
        # Add chat history before the current query
        messages.extend(chat_history)

        if route == "rag":
            # Retrieval
            try:
                chunks = self.qdrant_client.get_relevant_chunks(
                    content, top_k=settings.top_k_neighbors
                )
                if not chunks:
                    return "No relevant information found.", []

                # get doc title helper
                doc_title = (
                    lambda doc_id: s.query(Document.title)
                    .filter(Document.id == doc_id)
                    .first()[0]
                    if doc_id else "Unknown Document"
                )

                messages.append(("human", prompts.main_user_prompt.format(
                    context=[{"text": c.payload["text"], "source": doc_title(c.payload["document_id"])}
                             for c in chunks],
                    query=content
                )))
            except Exception as e:
                print(f"Error retrieving relevant information: {e}")
                return "Error retrieving relevant information.", []
        else:
            # Direct, no retrieval
            messages.append(("human", content))

        # Call LLM
        sources_list = []
        if route == "rag" and chunks:
            # get doc title helper (redefined for proper scope)
            doc_title = (
                lambda doc_id: s.query(Document.title)
                .filter(Document.id == doc_id)
                .first()[0]
                if doc_id else "Unknown Document"
            )
            # Format sources consistently for both providers
            sources_list = [
                {"text": c.payload["text"], "source": doc_title(c.payload["document_id"])}
                for c in chunks
            ]
        
        print(f"Generated {len(sources_list)} sources")
        for source in sources_list:
            print(f"Source: {source['source']}")
        
        if provider == "gemini":
            return self.generate_gemini(messages), sources_list
        elif provider == "openai":
            return self.generate_openai(messages), sources_list
        else:
            raise ValueError(f"Unsupported provider: {provider}")