# Security Rules

## Secrets
- NEVER hardcode secrets (API keys, passwords, tokens, connection strings).
- Use environment variables or secret manager.
- Check for leaked secrets before every commit: `sk-`, `api_key=`, `password=`.
- If a secret is exposed: rotate immediately, then fix.

## Input Validation
- Validate ALL user input at system boundaries.
- SQL: parameterized queries only. Never string concatenation.
- HTML: sanitize output to prevent XSS.
- File paths: prevent path traversal (`../`).
- URLs: validate scheme (https only for external).

## Authentication
- JWT tokens with expiration. httpOnly cookies for web.
- Rate limiting on all authentication endpoints.
- Error messages must not leak whether user/email exists.

## Dependencies
- Pin dependency versions. Review before upgrading.
- Run `npm audit` / `pip audit` periodically.
- Never install packages from untrusted sources.

## Logging
- Never log secrets, tokens, passwords, or PII.
- Log security events: failed auth, permission denied, rate limits.
- Include request IDs for correlation.
