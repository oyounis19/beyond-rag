# Beyond RAG

## About The Project

An end-to-end, self-hosted RAG system designed for intelligent document management with advanced conflict detection. This single-tenant system showcases sophisticated RAG capabilities including document contradiction detection, multiple LLM provider support, and comprehensive observability.

### Key Features

*   **Intelligent Document Processing**: Advanced document parsing with optional Docling support for PDFs, plus standard support for text, markdown, and Excel files.
*   **Smart Conflict Detection**: Automatically identifies contradictions and duplicates in your knowledge base using NLI models and LLM fallback analysis.
*   **Multiple LLM Providers**: Choose between OpenAI API, self-hosted VLLM models, or Groq for different use cases and privacy requirements.
*   **Real-time Processing Status**: Visual feedback showing document processing stages: parsing → chunking → embedding → conflict analysis.
*   **Bulk Conflict Resolution**: "Apply New Changes to All" functionality for efficient conflict management.
*   **Interactive Chat Interface**: RAG-powered chat with your documents using your preferred LLM provider.
*   **Comprehensive Observability**: Integrated with Langfuse for detailed tracing and analytics of all operations.
*   **Evaluation Framework**: Ready for DeepEval integration to assess system performance and quality.

### Demo Flow

The system is designed to demonstrate a complete RAG workflow:

1. **Document Upload**: Clean drag-and-drop interface with real-time processing status
2. **Conflict Detection**: Automatic identification of contradictions with visual comparison
3. **Conflict Resolution**: Side-by-side comparison with individual or bulk resolution options
4. **Knowledge Chat**: Intelligent conversation with your updated knowledge base
5. **Observability**: Direct links to Langfuse traces for complete transparency

### System Components

The system is composed of the following services, orchestrated with Docker Compose:

*   **`api`**: FastAPI application serving the main API with synchronous processing
*   **`frontend`**: React-based web interface for document management and chat
*   **`postgres`**: Single database for all application data
*   **`qdrant`**: Vector database for document embeddings and similarity search
*   **`minio`**: Self-hosted S3-compatible object storage for document files
*   **`langfuse`**: LLM observability platform for tracing and analytics
*   **`clickhouse`**: Analytics database for Langfuse

### Getting Started

Follow these steps to get the system running locally.

1. **Create Environment File**
   
   ```bash
   cp .env.sample .env
   ```

2. **Configure Environment**
   
   Open the `.env` file and configure your settings. At a minimum, you must set your LLM provider API keys (OpenAI, Groq, etc.).

3. **Launch Services**
   
   ```bash
   docker compose up -d --build
   ```

### Accessing Services

Once the containers are running, you can access the services at the following endpoints:

* **Main Application**: [http://localhost:5173](http://localhost:5173)
* **API Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
* **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **Langfuse UI**: [http://localhost:3000](http://localhost:3000)
* **MinIO Console**: [http://localhost:9091](http://localhost:9091)
* **Qdrant Console**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

### API Endpoints

The system provides a clean, single-tenant API:

* **Documents**: `POST /documents`, `GET /documents`, `POST /documents/{id}/publish?docling=true`
* **Conflicts**: `GET /conflicts`, `POST /conflicts/{id}/resolve`, `POST /conflicts/resolve-all`
* **Chat**: `POST /chat/sessions`, `GET /chat/sessions`, `POST /chat/sessions/{id}/messages`
* **Evaluations**: `POST /evals/tests`, `GET /evals/tests`, `POST /evals/runs`
