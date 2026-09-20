# Deployment

Local development supports SQLite and mock data. Docker Compose runs the API, web app, and PostgreSQL. Production requires TLS, secure secret storage, authentication, encrypted durable persistence, backups, monitoring, rate limiting, and an explicit review of broker permissions and current API terms. Do not expose the development approval-token endpoint or demo data without adding a real authenticated UI boundary.
