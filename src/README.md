# Backend (SmartRAG)

## Folder Structure

```md
└── 📁src
    └── 📁app
        └── 📁api
            ├── __init__.py
            ├── chat.py
            ├── conflicts.py
            ├── ingestion.py
        └── 📁models
            ├── __init__.py
            ├── app_models.py
        └── 📁providers
            ├── app_context.py
            ├── embeddings.py
            ├── llm.py
            ├── nli.py
            ├── prompts.py
            ├── qdrant_client.py
            ├── storage.py
        └── 📁services
            ├── ingestion_service.py
            ├── utils.py
        ├── __init__.py
        ├── config.py
        ├── database.py
        ├── main.py
    ├── .dockerignore
    ├── Dockerfile
    ├── README.md
    └── requirements.txt
```
