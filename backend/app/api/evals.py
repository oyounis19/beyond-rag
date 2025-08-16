from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid, datetime
from ..database import SessionLocal
from ..providers.app_context import AppContext
from ..models.app_models import EvalTest, EvalRun, EvalRunResult

router = APIRouter(prefix="/evals", tags=["Evaluations"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/tests")
def create_test(name: str, question: str, expected: str | None = None, tags: str | None = None, db: Session = Depends(get_db)):
    ctx = AppContext()
    s = ctx.get_db_session()
    try:
        test = EvalTest(name=name, question=question, expected=expected, tags=tags)
        s.add(test)
        s.commit()
        return {"test_id": str(test.id)}
    finally:
        ctx.close_session(s)

@router.get("/tests")
def list_tests(db: Session = Depends(get_db)):
    ctx = AppContext()
    s = ctx.get_db_session()
    try:
        tests = s.query(EvalTest).order_by(EvalTest.created_at.desc()).all()
        return [{"id": str(t.id), "name": t.name, "question": t.question, "expected": t.expected, "tags": t.tags, "created_at": t.created_at.isoformat()} for t in tests]
    finally:
        ctx.close_session(s)

@router.post("/runs")
def create_run(trigger: str = "manual", db: Session = Depends(get_db)):
    """Create a new evaluation run (placeholder for DeepEval integration)"""
    ctx = AppContext()
    s = ctx.get_db_session()
    try:
        run = EvalRun(trigger=trigger, summary_json={"status": "placeholder", "message": "DeepEval integration pending"})
        s.add(run)
        s.commit()
        return {"run_id": str(run.id), "status": "created"}
    finally:
        ctx.close_session(s)

@router.get("/runs")
def list_runs(db: Session = Depends(get_db)):
    """List all evaluation runs"""
    ctx = AppContext()
    s = ctx.get_db_session()
    try:
        runs = s.query(EvalRun).order_by(EvalRun.created_at.desc()).limit(50).all()
        out = []
        for r in runs:
            results = s.query(EvalRunResult).filter(EvalRunResult.run_id == r.id).all()
            out.append({
                "id": str(r.id),
                "trigger": r.trigger,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "summary": r.summary_json
            })
        return out
    finally:
        ctx.close_session(s)
