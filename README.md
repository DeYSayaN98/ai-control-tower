# AI Control Tower (MVP)
An AI gateway with governance built in: inventory, sensitive-data detection, policy enforcement,
approval workflow, tamper-evident audit log, explainable risk scores, dashboard.

## Run
    pip install -r requirements.txt
    python -m uvicorn app.main:app --reload   # dashboard at http://localhost:8000
    python demo.py                       # sends 4 realistic requests

Mock provider by default. `real_test.py` sends real prompts once a provider key is set. For real traffic set `UPSTREAM_API_KEY` (PowerShell: `$env:UPSTREAM_API_KEY="..."`) (OpenAI-compatible upstream via `UPSTREAM_URL`).
Client integration = change base URL + send `X-App-Id` and `X-User` headers.

## Layout
- `app/detect.py`   PII/secret detection (regex + Luhn; swap in Presidio later)
- `app/policy.py` + `policies/default.yaml`   rules: allow / redact / block / approve
- `app/db.py`       SQLite; hash-chained audit log (`/api/audit/verify`)
- `app/risk.py`     transparent 0-100 score (hover a row for factor breakdown)
- `app/main.py`     gateway + APIs (`/api/stats`, `/api/inventory`, `/api/events`, `/api/approvals`)
- `static/index.html`  responsive dashboard (desktop, tablet, phone; light/dark)

## Roadmap
Anthropic/Azure adapters and streaming, Postgres + ClickHouse, SSO/RBAC/multi-tenant,
MCP tool-call interception, shadow-AI discovery, EU AI Act / NIST AI RMF / ISO 42001 evidence reports.
