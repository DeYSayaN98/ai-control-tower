import hashlib, json, sqlite3, threading, time, uuid

_lock = threading.Lock()
conn = sqlite3.connect("control_tower.db", check_same_thread=False)
conn.row_factory = sqlite3.Row
conn.executescript("""
CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, ts REAL, app TEXT, user TEXT, model TEXT,
  action TEXT, policy TEXT, entities TEXT, preview TEXT, prev_hash TEXT, hash TEXT);
CREATE TABLE IF NOT EXISTS apps(app TEXT PRIMARY KEY, first_seen REAL, last_seen REAL,
  owner TEXT DEFAULT 'unassigned', autonomy INTEGER DEFAULT 1, requests INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS approvals(id TEXT PRIMARY KEY, ts REAL, app TEXT, user TEXT,
  status TEXT, entities TEXT, rule TEXT);
""")


def register_app(app, user):
    with _lock:
        now = time.time()
        conn.execute("INSERT OR IGNORE INTO apps(app,first_seen,last_seen) VALUES(?,?,?)", (app, now, now))
        conn.execute("UPDATE apps SET last_seen=?, requests=requests+1, owner=CASE WHEN owner='unassigned' THEN ? ELSE owner END WHERE app=?",
                     (now, user, app))
        conn.commit()


def log_event(app, user, model, action, policy, entities, preview):
    """Append-only audit log; each row hashes the previous one (tamper-evident)."""
    with _lock:
        row = conn.execute("SELECT hash FROM events ORDER BY ts DESC, rowid DESC LIMIT 1").fetchone()
        prev = row["hash"] if row else "GENESIS"
        eid, ts = uuid.uuid4().hex[:12], time.time()
        payload = json.dumps([eid, ts, app, user, model, action, policy, entities, preview, prev])
        h = hashlib.sha256(payload.encode()).hexdigest()
        conn.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                     (eid, ts, app, user, model, action, policy, json.dumps(entities), preview, prev, h))
        conn.commit()
        return eid


def verify_chain():
    prev = "GENESIS"
    for r in conn.execute("SELECT * FROM events ORDER BY ts, rowid"):
        payload = json.dumps([r["id"], r["ts"], r["app"], r["user"], r["model"], r["action"],
                              r["policy"], json.loads(r["entities"]), r["preview"], prev])
        if r["prev_hash"] != prev or hashlib.sha256(payload.encode()).hexdigest() != r["hash"]:
            return {"valid": False, "broken_at": r["id"]}
        prev = r["hash"]
    return {"valid": True}


def create_approval(app, user, entities, rule):
    aid = uuid.uuid4().hex[:10]
    with _lock:
        conn.execute("INSERT INTO approvals VALUES(?,?,?,?,?,?,?)",
                     (aid, time.time(), app, user, "pending", json.dumps(entities), rule))
        conn.commit()
    return aid


def rows(sql, args=()):
    with _lock:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]
