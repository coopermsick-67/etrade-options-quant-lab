# Deployment

Local development supports SQLite and starts with no market-data provider configured. Docker Compose runs the API, web app, and PostgreSQL. Production requires TLS, secure secret storage, authentication, encrypted durable persistence, backups, monitoring, rate limiting, and an explicit review of broker permissions and current API terms. Do not expose the development approval-token endpoint or any sample fixtures without adding a real authenticated UI boundary.
