# Beyond RAG

## About The Project

An end-to-end, self-hosted RAG system designed for intelligent document management with advanced **conflict detection**. This single-tenant system showcases sophisticated RAG capabilities including document contradiction detection, multiple LLM provider support, and comprehensive observability.

### Screenshots

**Conflict Detection Example**

![Conflict Detection Example](/media/v1.png)

![Conflict Detection Example 2](/media/v2.png)

**Chat Interface Example**

![Chat Interface Example](/media/chat.png)

### Key Features

*   **Intelligent Document Processing**: Advanced document parsing with optional Docling support for PDFs, plus standard support for text, markdown, and Excel files.
*   **Smart Conflict Detection**: Automatically identifies contradictions and duplicates in your knowledge base using NLI models and LLM fallback analysis.
*   **Multiple LLM Providers**: Choose between OpenAI API, Gemini API, Groq, or possibly self-hosted LLM via vLLM for different use cases and privacy requirements.
*   **Real-time Processing Status**: Visual feedback showing document processing stages: `parsing → chunking → embedding → conflict analysis`.
*   **Interactive Chat Interface**: RAG-powered chat with your documents using your preferred LLM provider.
*   **Comprehensive Observability**: Integrated with Langfuse for detailed tracing and analytics of all operations.

### System Components

The system is composed of the following services, orchestrated with Docker Compose:

*   **`api`**: FastAPI application serving the main API with synchronous processing
*   **`frontend`**: React-based web interface for document management and chat
*   **`postgres`**: Single database for all application data
*   **`qdrant`**: Vector database for document embeddings and similarity search
*   **`minio`**: Self-hosted S3-compatible object storage for document files
*   **`langfuse`**: LLM observability platform for tracing and analytics
*   **`clickhouse`**: Analytics database for Langfuse
*   **`redis`**: In-memory data structure store required by Langfuse

### Getting Started

Follow these steps to get the system running locally.

1. **Create Environment File**
   
   ```bash
   cp .env.sample .env
   ```

2. **Configure Environment**
   
   Open the `.env` file and configure your settings. At a minimum, you must set your LLM provider API keys (OpenAI, Groq, etc.).

3. **Run Services**
   
   ```bash
   docker compose up -d --build
   ```

4. **Grab Langfuse API keys & Update `.env`**
5. **Restart Services**
   
   ```bash
   docker compose restart
   ```

### Accessing Services

Once the containers are running, you can access the services at the following endpoints:

* **Main Application**: [http://localhost:5173](http://localhost:5173)
* **API Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
* **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **Langfuse UI**: [http://localhost:3000](http://localhost:3000)
* **MinIO Console**: [http://localhost:9091](http://localhost:9091)
* **Qdrant Console**: [http://localhost:6333/dashboard#/collections](http://localhost:6333/dashboard#/collections)
