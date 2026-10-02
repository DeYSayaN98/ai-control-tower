import fnmatch, pathlib, yaml

POLICY_FILE = pathlib.Path(__file__).parent.parent / "policies" / "default.yaml"


def load():
    return yaml.safe_load(POLICY_FILE.read_text())


def evaluate(entities, model, app_id):
    """Return (action, rule_name). First matching rule wins."""
    pol = load()
    ents = set(entities)
    for rule in pol.get("rules", []):
        if rule.get("models") and not any(fnmatch.fnmatch(model, m) for m in rule["models"]):
            continue
        if rule.get("apps") and app_id not in rule["apps"]:
            continue
        if ents & set(rule.get("entities", [])):
            return rule["action"], rule["name"]
    return pol.get("default_action", "allow"), "default"
