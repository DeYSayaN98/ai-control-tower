"""Demo: sends 6 requests. Two of them need human approval (KYC and loan)."""
import json
import httpx

URL = "http://localhost:8000/v1/chat/completions"
CASES = [
    ("support-copilot", "priya@bank.com", "Summarise the refund policy for me."),
    ("support-copilot", "priya@bank.com", "Customer Rahul, rahul.k@gmail.com, card 4111 1111 1111 1111 disputes a charge."),
    ("dev-agent", "arjun@bank.com", "Debug this: aws_key = AKIAIOSFODNN7EXAMPLE"),
    ("kyc-assistant", "meera@bank.com", "Verify PAN ABCDE1234F for this applicant."),
    ("loan-bot", "vikram@bank.com", "Check eligibility for applicant with Aadhaar 2345 6789 0123."),
]

pending = []
for app, user, text in CASES:
    r = httpx.post(URL, headers={"X-App-Id": app, "X-User": user},
                   json={"model": "gpt-4o", "messages": [{"role": "user", "content": text}]})
    print(f"{app:16} {r.status_code}  {r.text[:100]}")
    if r.status_code == 202:
        pending.append({"app": app, "user": user, "text": text,
                        "approval_id": r.json()["error"]["approval_id"]})

with open("pending.json", "w") as f:
    json.dump(pending, f, indent=2)

print(f"\n{len(pending)} requests are waiting for approval:")
for p in pending:
    print(f"  {p['approval_id']}  {p['app']}")
print("\nNext: open http://localhost:8000, APPROVE one and DENY the other, then run: python check.py")