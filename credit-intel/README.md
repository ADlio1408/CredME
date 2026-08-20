# Next-Gen Credit Intelligence — Underwriting Prototype

A real-time, explainable underwriting engine that scores a loan application
against a traditional credit-risk model and, optionally, fuses in a
behavioral/alternative-data trust signal derived from transaction history —
aimed at the "thin-file" / new-to-credit problem statement.

> **Read this first:** the two provided datasets (`Loan.csv`,
> `bank_transactions_data_2.csv`) do not share a customer key — they're
> different schemas with no common ID. Rather than fake a join, this
> prototype treats them as two real, independently-sourced signals and
> fuses them explicitly at the API layer (`fused_score = 0.8·traditional +
> 0.2·behavioral`), with the join point clearly marked for where a real
> Customer/Party ID would go in production. Say this plainly in your demo —
> it's a stronger answer than pretending the datasets are linked.

## What's actually here vs. the "ideal" architecture

The problem statement's target architecture lists Spring Boot, Postgres +
pgvector, AWS Bedrock, and a full cloud deployment. Given the timeline, this
prototype implements the same *shape* with faster-to-build, equivalent
technology, and documents the swap path for each:

| Target stack | What's built here | Swap path |
|---|---|---|
| Spring Boot API | **FastAPI (Python)** | Same REST contract; a Spring Boot port would implement the same 4 endpoints |
| PostgreSQL | **SQLite via SQLAlchemy** | Change one env var (`DATABASE_URL`) — see below |
| pgvector / semantic search | *Not implemented* | Noted in "Next steps" — no free-text corpus in the given data to justify it yet |
| AWS Bedrock LLM | **Claude API, pluggable** | Set `ANTHROPIC_API_KEY`; falls back to a deterministic template if unset, so the app runs with zero AI cost/dependency |
| AWS deployment | *Not deployed* | Runs locally; Dockerfile-ready structure, see "Next steps" |

This is an honest scoping choice, not an oversight — worth saying explicitly
in your submission deck.

## Architecture

```
┌─────────────────────┐        ┌──────────────────────────────┐
│   React Frontend     │  HTTP  │        FastAPI Backend        │
│  (single-page app,   │──────▶ │                                │
│   CDN React, no      │ X-API- │  /api/score      /api/behavior│
│   build step)        │  Key   │  /api/accounts   /api/health  │
└─────────────────────┘        │  /api/applications/recent      │
                                 │                                │
                                 │  ┌──────────────────────────┐ │
                                 │  │ ml/score.py               │ │
                                 │  │  GradientBoostingClassifier│ │
                                 │  │  trained on Loan.csv       │ │
                                 │  │  -> approval prob + ranked │ │
                                 │  │     feature contributions  │ │
                                 │  └──────────────────────────┘ │
                                 │  ┌──────────────────────────┐ │
                                 │  │ behavior.py                │ │
                                 │  │  behavioral trust score    │ │
                                 │  │  from bank_transactions.csv│ │
                                 │  └──────────────────────────┘ │
                                 │  ┌──────────────────────────┐ │
                                 │  │ explain.py (AI layer)      │ │
                                 │  │  Claude call w/ grounded    │ │
                                 │  │  prompt, template fallback │ │
                                 │  └──────────────────────────┘ │
                                 │              │                 │
                                 │       SQLAlchemy ORM           │
                                 └──────────────┼─────────────────┘
                                                 ▼
                                   SQLite (dev) / PostgreSQL (prod)
                                   — audit trail of every decision
```

**Decision separation, deliberately:** the ML model + fixed probability
thresholds make the APPROVE / REFER / DECLINE call. The LLM in `explain.py`
only *narrates* a decision already made from structured inputs, and its
prompt explicitly forbids inventing reasons not in the input. This is the
core "responsible AI" design choice for a regulated lending use case — an
LLM should explain a credit decision, not make it.

## Repo layout

```
credit-intel/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app & routes
│   │   ├── schemas.py       # Pydantic input/output contracts + validation
│   │   ├── security.py      # API key auth (fail-closed)
│   │   ├── config.py        # env-based config, no hardcoded secrets
│   │   ├── db.py            # SQLAlchemy models (SQLite/Postgres)
│   │   ├── behavior.py      # behavioral/alt-data scoring engine
│   │   ├── explain.py       # AI explanation layer (LLM + fallback)
│   │   └── ml/
│   │       ├── train_model.py   # trains + serializes the credit model
│   │       ├── score.py         # loads model, scores, explains
│   │       └── artifacts/       # model.pkl, scaler.pkl, importances (generated)
│   ├── data/                # Loan.csv, bank_transactions_data_2.csv
│   ├── tests/test_scoring.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── index.html           # React SPA (CDN React + Babel, zero build step)
└── README.md
```

## Setup & run

### 1. Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt

cp .env.example .env
# edit .env: set CREDIT_INTEL_API_KEY to any random string, e.g.
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# (ANTHROPIC_API_KEY is optional — leave blank to use the template explainer)

# train the model (writes backend/app/ml/artifacts/*)
python -m app.ml.train_model

# run the API
uvicorn app.main:app --reload --port 8000
```

Verify: `curl http://localhost:8000/api/health` → `{"status":"ok",...}`

### 2. Frontend

No build step needed — it's a single HTML file using React via CDN.

```bash
cd frontend
python3 -m http.server 5173
# open http://localhost:5173
```

In the left sidebar, set **API Connection → X-API-Key** to the same value
you put in `backend/.env`. Then fill out the application form and click
**Run Underwriting Score**.

To see behavioral fusion in action, enter a demo Account ID such as
`AC00128`, `AC00455`, or `AC00019` (pulled from `bank_transactions_data_2.csv`)
in the "Behavioral Fusion" field before submitting.

### 3. Tests

```bash
cd backend
pytest tests/ -v
```

Covers: model discriminates good vs. risky applicants correctly, decision
thresholds behave as documented, explanation factors are ranked and bounded,
behavioral engine handles unknown accounts and edge cases (accounts with
very few transactions) without producing NaN or out-of-range scores — this
last one caught a real bug during development (std-dev of a single-gap
sample is undefined; see `behavior.py`).

## Security notes

- No secrets are hardcoded anywhere; `config.py` reads only from environment
  variables, loaded via `.env` (gitignored) locally or a real secret manager
  in production.
- `/api/score`, `/api/behavior`, `/api/accounts`, `/api/applications/recent`
  all require a valid `X-API-Key` header, checked with a constant-time
  comparison (`hmac.compare_digest`) to avoid timing side-channels. The
  server **fails closed**: if no key is configured server-side, all
  protected routes return 503 rather than silently allowing access.
- All request input is validated by Pydantic (`schemas.py`) with explicit
  ranges (e.g. `credit_score` must be 300–850) before it ever reaches the
  model — malformed input is rejected at the boundary, not deep in
  business logic.
- CORS is restricted to an explicit origin allow-list (`CORS_ORIGINS`), not
  `*`.

## Responsible AI / explainability

- **Auditability**: every scored application is persisted (`applications`
  table) with its decision, score, and explanation — a basic audit trail.
- **Explainability**: `credit_intel_score` comes with a ranked list of the
  features that most influenced it (`top_factors`), computed from the
  model's feature importances weighted by how far the applicant deviates
  from the training population on each feature. This is an approximation
  (see `score.py` docstring) — the natural next step is a proper SHAP
  TreeExplainer, which the code is structured to drop in without touching
  the API contract.
- **Guardrails on the LLM layer**: the system prompt in `explain.py`
  explicitly forbids the model from inventing reasons not present in the
  structured factors, and from referencing protected characteristics. If
  the LLM call fails or no API key is set, scoring still works via a
  deterministic template — the AI layer is additive narration, never a
  single point of failure for the underwriting decision itself.
- **Bias caveat (be upfront about this in your demo)**: this model is
  trained on one static dataset with no fairness audit performed. `Age` is
  used as a feature in the traditional model — flag this explicitly as a
  "next steps" item (disparate-impact testing, considering whether age
  should be excluded or handled via a fairness-constrained model) rather
  than presenting the prototype as production-ready.

## Next steps (what to say when asked "what would you build next")

1. **Real SHAP explainability** instead of the importance × z-score
   approximation currently used.
2. **Disparate impact / fairness testing** across protected-adjacent
   proxies before this ever touches real applicants.
3. **True customer-ID join** between bureau data and transaction data,
   instead of the demo's account-ID lookup.
4. **pgvector-backed semantic search** over underwriting policy documents,
   so the LLM layer can cite specific policy clauses in its explanation
   rather than only the model's numeric factors — this is where the
   "vector DB" piece of the target architecture actually earns its keep.
5. **Postgres in production** — already a one-line `DATABASE_URL` change.
6. **OAuth2/JWT with per-underwriter scopes**, replacing the shared API key.
7. **Containerize + deploy** (Dockerfile per service, behind an API gateway).
