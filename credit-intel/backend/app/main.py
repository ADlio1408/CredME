"""
Next-Gen Credit Intelligence - API service.

Endpoints:
  GET  /api/health                          liveness check, no auth
  GET  /api/accounts                         list demo AccountIDs available for behavioral fusion
  GET  /api/behavior/{account_id}             behavioral trust score for one account
  POST /api/score                             score a loan application (traditional + optional behavioral fusion)
  GET  /api/applications/recent               last N stored decisions (audit trail)

Run: uvicorn app.main:app --reload
"""
import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app import behavior, db, explain
from app.config import settings
from app.ml import score as ml_score
from app.schemas import ScoreResponse
from app.schemas import LoanApplication
from app.security import require_api_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("credit_intel")

app = FastAPI(
    title="Next-Gen Credit Intelligence API",
    description="Real-time, explainable underwriting engine combining bureau-style "
                 "credit data with behavioral/alternative signals.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    db.init_db()
    logger.info("Database initialized (%s)", settings.database_url)


@app.get("/api/health")
def health():
    return {"status": "ok", "env": settings.env}


@app.get("/api/accounts", dependencies=[Depends(require_api_key)])
def get_accounts():
    """Demo helper: lists AccountIDs present in the sample transaction data
    so the frontend can offer a picker for behavioral fusion in the demo."""
    return {"accounts": behavior.list_accounts()[:50]}


@app.get("/api/behavior/{account_id}", dependencies=[Depends(require_api_key)])
def get_behavior(account_id: str):
    profile = behavior.get_behavior_profile(account_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"No transaction history for account {account_id}")
    return profile


@app.post("/api/score", response_model=ScoreResponse, dependencies=[Depends(require_api_key)])
def score(application: LoanApplication, session: Session = Depends(db.get_db)):
    app_dict = application.model_dump()

    result = ml_score.score_application(app_dict)

    behavioral_profile = None
    fused_score = None
    if application.account_id:
        behavioral_profile = behavior.get_behavior_profile(application.account_id)
        if behavioral_profile:
            # Fusion: bureau/traditional score carries most of the weight
            # (it's outcome-validated in this dataset); behavioral score is
            # a supplementary adjustment, capped so it can nudge but never
            # flip a strongly-decided case on its own.
            trust = behavioral_profile["behavioral_trust_score"]
            fused_score = round(0.8 * result["credit_intel_score"] + 0.2 * trust, 1)

    explanation = explain.generate_explanation(
        result["decision"], result["top_factors"], behavioral_profile
    )

    response = {
        **result,
        "behavioral_trust_score": behavioral_profile["behavioral_trust_score"] if behavioral_profile else None,
        "behavioral_signals": behavioral_profile["signals"] if behavioral_profile else None,
        "fused_score": fused_score,
        "explanation": explanation,
        "model_version": ml_score.MODEL_VERSION,
    }

    db.save_application(
        session,
        account_id=application.account_id,
        input_payload=app_dict,
        result=response,
    )

    return response


@app.get("/api/applications/recent", dependencies=[Depends(require_api_key)])
def recent_applications(limit: int = 10, session: Session = Depends(db.get_db)):
    limit = max(1, min(limit, 100))
    records = (
        session.query(db.ApplicationRecord)
        .order_by(db.ApplicationRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "created_at": r.created_at.isoformat(),
            "account_id": r.account_id,
            "decision": r.decision,
            "credit_intel_score": r.credit_intel_score,
            "fused_score": r.fused_score,
        }
        for r in records
    ]
