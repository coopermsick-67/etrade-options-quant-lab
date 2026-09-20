-- Initial durable schema. Apply through the deployment migration runner.
-- Secrets and OAuth token material are intentionally absent from this schema.

CREATE TABLE IF NOT EXISTS market_snapshots (
  id INTEGER PRIMARY KEY,
  provider VARCHAR(80) NOT NULL,
  symbol VARCHAR(32) NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL,
  payload JSONB NOT NULL,
  quality_status VARCHAR(24) NOT NULL
);

CREATE TABLE IF NOT EXISTS candidates (
  id VARCHAR(64) PRIMARY KEY,
  strategy VARCHAR(80) NOT NULL,
  underlying VARCHAR(32) NOT NULL,
  model_version VARCHAR(80) NOT NULL,
  config_version VARCHAR(80) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  payload JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS trade_tickets (
  id VARCHAR(64) PRIMARY KEY,
  ticket_hash VARCHAR(64) NOT NULL,
  environment VARCHAR(16) NOT NULL,
  status VARCHAR(32) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  payload JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
  id VARCHAR(64) PRIMARY KEY,
  ticket_hash VARCHAR(64) NOT NULL,
  actor VARCHAR(32) NOT NULL,
  issued_at TIMESTAMPTZ NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  consumed_at TIMESTAMPTZ,
  used BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS broker_orders (
  id VARCHAR(64) PRIMARY KEY,
  client_order_id VARCHAR(128) NOT NULL UNIQUE,
  ticket_id VARCHAR(64),
  broker VARCHAR(32) NOT NULL,
  environment VARCHAR(16) NOT NULL,
  status VARCHAR(32) NOT NULL,
  submitted_at TIMESTAMPTZ NOT NULL,
  payload JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS positions (
  id INTEGER PRIMARY KEY,
  broker VARCHAR(32) NOT NULL,
  environment VARCHAR(16) NOT NULL,
  symbol VARCHAR(64) NOT NULL,
  quantity INTEGER NOT NULL,
  average_price NUMERIC(18, 8) NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS experiments (
  id VARCHAR(64) PRIMARY KEY,
  strategy_id VARCHAR(80) NOT NULL,
  git_sha VARCHAR(64) NOT NULL,
  dataset_hash VARCHAR(64) NOT NULL,
  started_at TIMESTAMPTZ NOT NULL,
  config JSONB NOT NULL,
  metrics JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
  id INTEGER PRIMARY KEY,
  timestamp TIMESTAMPTZ NOT NULL,
  event_type VARCHAR(80) NOT NULL,
  actor VARCHAR(32) NOT NULL,
  environment VARCHAR(16) NOT NULL,
  trade_ticket_id VARCHAR(64),
  order_id VARCHAR(64),
  reason TEXT,
  result VARCHAR(32) NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_market_snapshots_symbol_time ON market_snapshots(symbol, captured_at);
CREATE INDEX IF NOT EXISTS idx_audit_events_type_time ON audit_events(event_type, timestamp);
