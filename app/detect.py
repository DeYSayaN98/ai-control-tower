import re

PATTERNS = {
    "PRIVATE_KEY": (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", 10),
    "AWS_KEY": (r"\bAKIA[0-9A-Z]{16}\b", 10),
    "API_KEY": (r"\b(?:sk|pk)-[A-Za-z0-9_-]{20,}\b", 10),
    "CREDIT_CARD": (r"\b(?:\d[ -]?){13,16}\b", 9),
    "US_SSN": (r"\b\d{3}-\d{2}-\d{4}\b", 9),
    "AADHAAR": (r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b", 9),
    "PAN": (r"\b[A-Z]{5}\d{4}[A-Z]\b", 8),
    "EMAIL": (r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", 4),
    "PHONE": (r"(?<!\d)(?:\+91[- ]?)?[6-9]\d{9}(?!\d)", 4),
}
COMPILED = {k: (re.compile(p), w) for k, (p, w) in PATTERNS.items()}


def _luhn(s: str) -> bool:
    d = [int(c) for c in s if c.isdigit()]
    if not 13 <= len(d) <= 16:
        return False
    total = 0
    for i, n in enumerate(reversed(d)):
        if i % 2:
            n = n * 2 - 9 if n * 2 > 9 else n * 2
        total += n
    return total % 10 == 0


def scan(text: str):
    """Return non-overlapping findings: [{entity, start, end}] sorted by position."""
    found = []
    for name, (rx, _) in COMPILED.items():
        for m in rx.finditer(text):
            if name == "CREDIT_CARD" and not _luhn(m.group()):
                continue
            found.append({"entity": name, "start": m.start(), "end": m.end()})
    found.sort(key=lambda f: (f["start"], -(f["end"] - f["start"])))
    out, last = [], -1
    for f in found:
        if f["start"] >= last:
            out.append(f)
            last = f["end"]
    return out


def redact(text: str, findings) -> str:
    for f in sorted(findings, key=lambda f: f["start"], reverse=True):
        text = text[: f["start"]] + f"[{f['entity']}]" + text[f["end"]:]
    return text


def sensitivity(entities) -> int:
    return max((PATTERNS[e][1] for e in entities), default=0)
