# Development

Use Python 3.12+, `uv`, Node 22+, and npm. Install Python dependencies with `uv sync --extra dev`, run `uv run ruff check .` and `uv run pytest`, then build the dashboard with `npm install && npm run build` in `apps/web`.

Do not use real broker credentials in tests. Mock HTTP responses. Run `python scripts/secret_scan.py` before a commit.
