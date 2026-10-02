import os, json, pathlib
import httpx
from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from . import db, detect, policy, risk

app = FastAPI(title="AI Control Tower")
STATIC = pathlib.Path(__file__).parent.parent / "static"

PROVIDERS = {  # name: (url, env var holding the key)
    "openai": ("https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY"),
    "anthropic": ("https://api.anthropic.com/v1/chat/completions", "ANTHROPIC_API_KEY"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "GEMINI_API_KEY"),
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY"),
}


def pick_provider(model: str):
    m = model.lower()
    if m.startswith("claude"):
        return "anthropic"
    if m.startswith("gemini"):
        return "gemini"
    if m.startswith(("llama", "mixtral", "gemma", "qwen", "openai/")):
        return "groq"
    return "openai"


def _text(msg):
    c = msg.get("content", "")
    return c if isinstance(c, str) else " ".join(p.get("text", "") for p in c if isinstance(p, dict))


@app.post("/v1/chat/completions")
async def chat(body: dict, x_app_id: str = Header("unregistered-app"), x_user: str = Header("anonymous"),
               x_approval_id: str | None = Header(None)):
    model = body.get("model", "unknown")
    db.register_app(x_app_id, x_user)

    # 1. scan every message
    per_msg = [detect.scan(_text(m)) for m in body.get("messages", [])]
    entities = sorted({f["entity"] for fs in per_msg for f in fs})
    action, rule = policy.evaluate(entities, model, x_app_id)
    preview = _text(body["messages"][-1])[:80] if body.get("messages") else ""
    preview = detect.redact(preview, detect.scan(preview))  # never store raw sensitive data

    # 2. enforce
    if action == "approve":
        st = db.rows("SELECT status FROM approvals WHERE id=?", (x_approval_id,)) if x_approval_id else []
        if st and st[0]["status"] == "denied":
            db.log_event(x_app_id, x_user, model, "block", "approval-denied", entities, preview)
            return JSONResponse({"error": {"type": "approval_denied",
                                           "message": "A reviewer denied this request."}}, status_code=403)
        ok = x_approval_id and db.rows("SELECT 1 FROM approvals WHERE id=? AND status='approved'", (x_approval_id,))
        if not ok:
            aid = db.create_approval(x_app_id, x_user, entities, rule)
            db.log_event(x_app_id, x_user, model, "pending_approval", rule, entities, preview)
            return JSONResponse({"error": {"type": "approval_required", "approval_id": aid,
                                           "message": "Request held for human approval."}}, status_code=202)
        action = "allow_approved"
    if action == "block":
        db.log_event(x_app_id, x_user, model, "block", rule, entities, preview)
        return JSONResponse({"error": {"type": "policy_violation", "policy": rule,
                                       "message": f"Blocked by policy '{rule}': {', '.join(entities)}"}}, status_code=403)
    if action == "redact":
        for m, fs in zip(body["messages"], per_msg):
            if fs and isinstance(m.get("content"), str):
                m["content"] = detect.redact(m["content"], fs)

    # 3. forward to the right provider (or mock when no key is set)
    provider = pick_provider(model)
    url, key_env = PROVIDERS[provider]
    key = os.getenv(key_env, "")
    if key:
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post(url, json=body, headers={"Authorization": f"Bearer {key}"})
            resp = r.json()
        except Exception as e:
            db.log_event(x_app_id, x_user, model, "provider_error", provider, entities, preview)
            return JSONResponse({"error": {"type": "provider_unreachable", "message": str(e)}}, status_code=502)
        if r.status_code >= 400:
            db.log_event(x_app_id, x_user, model, "provider_error", provider, entities, preview)
            return JSONResponse(resp, status_code=r.status_code)
    else:
        resp = {"id": "mock", "object": "chat.completion", "model": model, "choices": [
            {"index": 0, "finish_reason": "stop", "message": {"role": "assistant",
             "content": f"[mock: no {key_env} set] I received: " + _text(body["messages"][-1])[:200]}}]}

    # 4. scan the response too
    try:
        out = resp["choices"][0]["message"]["content"]
        of = detect.scan(out)
        if of:
            resp["choices"][0]["message"]["content"] = detect.redact(out, of)
            entities = sorted(set(entities) | {f["entity"] for f in of})
            action = "allow_approved" if action == "allow_approved" else "redact"
    except (KeyError, IndexError, TypeError):
        pass

    db.log_event(x_app_id, x_user, model, action, rule, entities, preview)
    return resp


class Decision(BaseModel):
    approve: bool


@app.get("/api/events")
def events(limit: int = 50):
    rs = db.rows("SELECT * FROM events ORDER BY ts DESC LIMIT ?", (limit,))
    for r in rs:
        r["entities"] = json.loads(r["entities"])
    return rs


@app.get("/api/stats")
def stats():
    by = {r["action"]: r["n"] for r in db.rows("SELECT action, COUNT(*) n FROM events GROUP BY action")}
    return {"total": sum(by.values()), "by_action": by,
            "apps": db.rows("SELECT COUNT(*) n FROM apps")[0]["n"],
            "pending": db.rows("SELECT COUNT(*) n FROM approvals WHERE status='pending'")[0]["n"]}


@app.get("/api/inventory")
def inventory():
    return risk.score_apps()


@app.post("/api/apps/{app_id}")
def update_app(app_id: str, owner: str | None = None, autonomy: int | None = None):
    if owner:
        db.conn.execute("UPDATE apps SET owner=? WHERE app=?", (owner, app_id))
    if autonomy:
        db.conn.execute("UPDATE apps SET autonomy=? WHERE app=?", (max(1, min(5, autonomy)), app_id))
    db.conn.commit()
    return {"ok": True}


@app.get("/api/approvals")
def approvals():
    rs = db.rows("SELECT * FROM approvals ORDER BY ts DESC")
    for r in rs:
        r["entities"] = json.loads(r["entities"])
    return rs


@app.post("/api/approvals/{aid}")
def decide(aid: str, d: Decision):
    db.conn.execute("UPDATE approvals SET status=? WHERE id=?", ("approved" if d.approve else "denied", aid))
    db.conn.commit()
    return {"ok": True}


@app.get("/api/audit/verify")
def verify():
    return db.verify_chain()


@app.get("/")
def dash():
    return FileResponse(STATIC / "index.html")