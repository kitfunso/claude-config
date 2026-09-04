# Security Rules

## Secrets
- Read secrets from the environment or a secret manager. Never write a literal key,
  password, token, connection string or PII into code, a log, a test assertion, a
  brief or an inventory file.
- Grep the staged diff for `sk-`, `api_key=`, `password=` before every commit.
- A leaked secret gets rotated first, then fixed.
- Log the security event and never the credential: failed auth, permission denied,
  rate limit, each with a request id.
