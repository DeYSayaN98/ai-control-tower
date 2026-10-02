import sqlite3, sys

c = sqlite3.connect("control_tower.db")
if len(sys.argv) > 1 and sys.argv[1] == "undo":
    c.execute("UPDATE events SET action='block' WHERE action='tampered'")
    print("Restored. The audit log should be intact again.")
else:
    row = c.execute("SELECT id FROM events WHERE action='block' LIMIT 1").fetchone()
    if not row:
        print("No blocked event found. Run python demo.py first.")
    else:
        c.execute("UPDATE events SET action='tampered' WHERE id=?", row)
        print(f"Changed event {row[0]} from 'block' to 'tampered' (fake edit).")
c.commit()