# Security

Keep E*TRADE consumer keys, OAuth tokens, token secrets, app secrets, and approval secrets in environment variables or an OS secrets manager. `.env` is ignored. Secrets must never enter frontend bundles, local storage, logs, screenshots, database plaintext fields, fixtures, or documentation.

The adapter uses OAuth 1.0a through `requests-oauthlib`; cryptography is delegated to the audited library. Structured logs should redact authorization headers, secrets, verifier codes, and complete account identifiers. Production deployments need encrypted secret storage, secure/httpOnly same-site cookies, CSRF/origin validation, access logs, rate limiting, dependency scanning, backups, and least privilege.

Treat quote and account data as sensitive. Mask account IDs. Validate all user inputs and strategy parameters. Never allow arbitrary code execution through configuration. The local single-user MVP is not a complete internet-facing authentication system.

Run the repository secret scanner before every push. If it reports a likely credential, stop and inspect; do not push around the finding.
