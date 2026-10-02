"""Send real requests through the gateway. Edit MODEL to match your provider."""
import httpx

URL = "http://localhost:8000/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"
TESTS = [
    "Explain what a credit score is in two sentences.",
    "Write a polite reply to a customer at rahul.k@gmail.com who called from 9876543210.",
    "Why does this fail? aws_key = AKIAIOSFODNN7EXAMPLE",
]
for t in TESTS:
    r = httpx.post(URL, timeout=60, headers={"X-App-Id": "my-first-app", "X-User": "sayan"},
                   json={"model": MODEL, "messages": [{"role": "user", "content": t}]})
    print(r.status_code, r.text[:300], "\n")
