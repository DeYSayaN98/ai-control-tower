"""Real test across OpenAI, Gemini and Groq. Edit MODELS if a name is rejected (404 / model not found)."""
import httpx

URL = "http://localhost:8000/v1/chat/completions"
# MODELS = ["gpt-4o-mini", "gemini-2.0-flash", "llama-3.3-70b-versatile"]
MODELS = ["gemini-flash-latest", "openai/gpt-oss-120b"]
PROMPTS = [
    "Say hello in five words.",
    "Reply to rahul.k@gmail.com, phone 9876543210, about his loan.",
    "Fix this: aws_key = AKIAIOSFODNN7EXAMPLE",
]
for m in MODELS:
    for p in PROMPTS:
        r = httpx.post(URL, timeout=60, headers={"X-App-Id": "multi-test", "X-User": "sayan"},
                       json={"model": m, "messages": [{"role": "user", "content": p}]})
        print(f"{m:26} {r.status_code}  {r.text[:90]}")
    print()