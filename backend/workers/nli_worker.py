# Placeholder NLI worker (static implementation)
# Real implementation will perform neighbor search + NLI classification
from rq import get_current_job

def nli_version(tenant_id: str, version_id: str):
    job = get_current_job()
    # Future steps:
    # 1. Fetch new chunks
    # 2. Vector neighbor search (Qdrant)
    # 3. Run NLI for contradictions
    # 4. Persist contradictions rows
    return {"tenant_id": tenant_id, "version_id": version_id, "nli_done": True, "contradictions": 0}
