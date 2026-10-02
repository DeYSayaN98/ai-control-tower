"""Transparent, rule-based risk score (0-100). Every point is explainable."""
import json
from . import db
from .detect import sensitivity


def score_apps():
    out = []
    for a in db.rows("SELECT * FROM apps"):
        evs = db.rows("SELECT action, entities FROM events WHERE app=?", (a["app"],))
        ents = {e for ev in evs for e in json.loads(ev["entities"])}
        sens = sensitivity(ents)
        blocked = sum(1 for e in evs if e["action"] == "block")
        factors = {
            "data_sensitivity": sens * 4,                      # max 40
            "autonomy_level": min(a["autonomy"], 5) * 6,       # max 30 (1=chat ... 5=fully autonomous)
            "policy_violations": min(blocked * 5, 20),         # max 20
            "unowned": 10 if a["owner"] == "unassigned" else 0,
        }
        total = min(sum(factors.values()), 100)
        level = "critical" if total >= 75 else "high" if total >= 50 else "medium" if total >= 25 else "low"
        out.append({**a, "risk": total, "level": level, "factors": factors, "entities_seen": sorted(ents)})
    return sorted(out, key=lambda x: -x["risk"])
