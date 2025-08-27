import json
import asyncio
from sqlalchemy.orm import Session
from json_repair import repair_json

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from langfuse import Langfuse, get_client
from langfuse.langchain import CallbackHandler
from ..config import settings
from ..models.app_models import Document
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

    def _route(self, query: str, chat_history: list = None) -> tuple[str, str]:
        """
        Decide if query needs RAG or not, and refine query if RAG is chosen.
        Returns: (route_decision, refined_query)
        """
        # Prepare conversation context from chat history
        conversation_context = ""
        if chat_history and len(chat_history) > 0:
            # Take last 3 turns (6 messages: 3 user + 3 assistant)
            recent_turns = chat_history[-6:] if len(chat_history) > 6 else chat_history
            context_lines = []
            for role, content in recent_turns:
                if role == "human":
                    context_lines.append(f"User: {content}")
                elif role == "assistant":
                    # Truncate long assistant responses for context
                    truncated_content = content[:200] + "..." if len(content) > 200 else content
                    context_lines.append(f"Assistant: {truncated_content}")
            conversation_context = "\n".join(context_lines)
        else:
            conversation_context = "No previous conversation."
        
        resp = self.conflict_llm.invoke([("system", prompts.router_prompt.format(
            conversation_context=conversation_context,
            query=query
        ))])
        
        try:
            # Parse JSON response
            response_content = resp.content.strip()
            print(f"Router raw response: {response_content}")
            
            # Try to parse as JSON
            try:
                router_result = json.loads(response_content)
            except json.JSONDecodeError:
                # Try to repair JSON if it's malformed
                router_result = json.loads(repair_json(response_content))
            
            route = router_result.get("route", "direct").lower()
            refined_query = router_result.get("refined_query", query)
            reasoning = router_result.get("reasoning", "")
            
            print(f"Router decision: {route}")
            print(f"Router reasoning: {reasoning}")
            if route == "rag":
                print(f"Refined query: {refined_query}")
            
            return route, refined_query
            
        except Exception as e:
            print(f"Router JSON parsing error: {e}, falling back to simple routing")
            # Fallback: try to extract route from response text
            response_lower = resp.content.strip().lower()
            if "rag" in response_lower:
                return "rag", query  # Use original query as fallback
            else:
                return "direct", query
    
    async def predict_conflict(self, llm: ChatGroq, chunk1: str, chunk2: str, semaphore: asyncio.Semaphore, conflict_payload: dict) -> dict:
        """
        Wrapper for the LLM call to format the output.
        """
        messages = [
            ("system", prompts.conflict_sys_prompt.template),
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

        # 1) Routing Decision - pass chat history for context and get refined query
        route, refined_query = self._route(content, chat_history)
        print(f"Router decision: {route}")
        if route == "rag":
            print(f"Using refined query for retrieval: {refined_query}")

        messages = [("system", prompts.main_sys_prompt.template)]
        
        # Add chat history before the current query
        messages.extend(chat_history)

        if route == "rag":
            # Retrieval using refined query for better results
            try:
                chunks = self.qdrant_client.get_relevant_chunks(
                    refined_query, top_k=settings.top_k_neighbors  # Use refined query here
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
                    query=content  # Keep original user query in the prompt for natural response
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