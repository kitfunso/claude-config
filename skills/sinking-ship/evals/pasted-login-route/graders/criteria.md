---
type: llm
weight: 2
---

/login builds SQL with an f-string (injectable), compares the password in plaintext (no hashing), and has no visible rate limiting. Pass only if all of the following hold:

1. SECURITY: flags the f-string SQL query as injectable (input not sanitized/parameterized), citing the query line.
2. SECURITY: flags the plaintext password comparison as failing to hash with bcrypt/argon2.
3. SECURITY: flags the absence of rate limiting on the login endpoint (FAIL or UNKNOWN with a note that none is visible — not PASS).
4. The overall ship verdict is "not ready".
5. Items this snippet can't show (HTTPS, firewall, backups, other routes) are marked UNKNOWN, not assumed PASS; it does not claim to have edited api.py (there is no Edit tool in this run, and no file to write to).

Fail if the verdict is "ready" or "ready with caveats", or if it misses the SQL injection.
