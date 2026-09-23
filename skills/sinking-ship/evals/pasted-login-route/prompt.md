---
name: pasted-login-route
tags: [sinking-ship, gate, ro]
plugins: ["../.."]
runs: 3
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

This is the whole of a tiny internal service (api.py, pasted below) — there's no repo here, no other files. Run the sinking-ship checklist against it before we put it live:

```python
from flask import Flask, request
import sqlite3

app = Flask(__name__)


@app.route("/login", methods=["POST"])
def login():
    user = request.form["user"]
    pw = request.form["pw"]
    con = sqlite3.connect("app.db")
    row = con.execute(
        f"SELECT * FROM users WHERE user='{user}' AND pw='{pw}'"
    ).fetchone()
    if row:
        return {"ok": True}
    return {"ok": False}, 401
```
