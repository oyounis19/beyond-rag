# Backend (SmartRAG)

Endpoints added:
- POST /tenants
- GET /tenants
- GET /health

Notes
- SQLAlchemy Base and engine are in app/database.py
- Control-plane model Tenant in app/models/control.py
- Simple create_all at import for MVP; swap to Alembic later.
