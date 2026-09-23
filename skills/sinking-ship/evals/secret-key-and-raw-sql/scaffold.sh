#!/usr/bin/env bash
set -euo pipefail
mkdir -p static
cat > static/app.js <<'EOF'
const OPENAI_API_KEY = "sk-proj-abcdefghijklmnopqrstuvwxyz0123456789ABCD";

async function askAssistant(prompt) {
  return fetch("https://api.openai.com/v1/chat/completions", {
    headers: { Authorization: `Bearer ${OPENAI_API_KEY}` },
  });
}
EOF
cat > db.py <<'EOF'
import sqlite3


def get_user(user_id):
    con = sqlite3.connect("app.db")
    query = "SELECT * FROM users WHERE id = " + user_id
    return con.execute(query).fetchall()
EOF
git init -q
git -c user.name=t -c user.email=t@t add -A
git -c user.name=t -c user.email=t@t commit -qm "chore: init tiny app"
