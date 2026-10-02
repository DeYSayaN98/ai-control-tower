"""Retries each held request with its approval ID and shows what the gateway decided."""
import json
import httpx

URL = "http://localhost:8000/v1/chat/completions"
for p in json.load(open("pending.json")):
    r = httpx.post(URL, headers={"X-App-Id": p["app"], "X-User": p["user"],
                                 "X-Approval-Id": p["approval_id"]},
                   json={"model": "gpt-4o", "messages": [{"role": "user", "content": p["text"]}]})
    if r.status_code == 200:
        verdict = "APPROVED, request went through"
    elif r.status_code == 403:
        verdict = "DENIED, request rejected"
    else:
        verdict = "NOT APPROVED YET (held again)"
    print(f"{p['app']:16} {p['approval_id']}  ->  {r.status_code}  {verdict}")