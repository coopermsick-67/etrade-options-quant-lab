import { useCallback, useEffect, useState } from "react";

type EquityPoint = { label: string; value: number };
type RiskLimit = { label: string; value: number; used: number };
type DataStatus = {
  provider: string;
  status: string;
  configured: boolean;
  source: string | null;
  quote_timestamp: string | null;
  message: string;
};
type Candidate = {
  candidate_id: string;
  underlying: string;
  strategy: string;
  expiration: string;
  dte: number;
  bid: number;
  ask: number;
  spread_pct: number;
  implied_volatility: number;
  realized_volatility: number | null;
  forecast_volatility: number;
  probability_profit: number;
  probability_interval: [number, number];
  max_loss: number;
  max_profit: number;
  net_ev: number;
  risk_adjusted_edge: number;
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
  status: string;
  legs: Array<{ action: string; strike: number; option_type: string; price: number }>;
  assumptions: string[];
};
type PaperOrder = {
  order_id: string;
  client_order_id: string;
  symbol: string;
  action: string;
  quantity: number;
  filled_quantity: number;
  limit_price: number;
  bid: number;
  ask: number;
  multiplier: number;
  status: string;
  reason: string | null;
  submitted_at: string;
  fill: { price: number; fees: number; quantity: number; timestamp: string } | null;
};
type PaperPosition = { symbol: string; quantity: number; average_price: number; multiplier: number };
type Dashboard = {
  mode: string;
  demo: boolean;
  data_status: DataStatus;
  broker_status: { etrade: string; robinhood: string };
  live_enabled: boolean;
  account: {
    equity: number;
    daily_pnl: number;
    buying_power: number;
    open_risk: number;
    portfolio_delta: number;
    portfolio_vega: number;
    cash: number;
    drawdown: number;
  };
  equity_curve: EquityPoint[];
  risk_limits: RiskLimit[];
  candidates: Candidate[];
  recent_activity: Array<{ time: string; symbol: string; action: string; details: string; status: string }>;
  model_health: {
    status: string;
    signal_win_rate: number | null;
    average_trade_expectancy: number | null;
    sharpe: number | null;
    max_drawdown: number | null;
    trades_analyzed: number;
    note: string;
  };
  paper: { emergency_stop: boolean; positions: PaperPosition[]; orders: PaperOrder[] };
};
type PublicSettings = {
  mode: string;
  market_data_provider: string;
  etrade_environment: string;
  live_enabled: boolean;
  risk: Record<string, number>;
};
type ChainContract = {
  option_symbol: string;
  option_type: string;
  strike: number;
  bid: number;
  ask: number;
  volume: number;
  open_interest: number;
  implied_volatility: number | null;
  delta: number | null;
  gamma: number | null;
  theta: number | null;
  vega: number | null;
};

const configuredApiBase = import.meta.env.VITE_API_URL as string | undefined;
const apiBase = configuredApiBase?.replace(/\/$/, "") ?? "";

const iconPaths: Record<string, string> = {
  overview: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
  scanner: "M4 5h16M7 12h10M10 19h4",
  chain: "M5 5h14v14H5zM8 9h8M8 13h8M8 17h5",
  backtests: "M4 19V5m0 14h16M8 16l3-4 3 2 4-6",
  paper: "M6 4h12v16H6zM9 8h6M9 12h6M9 16h4",
  portfolio: "M4 7h16v12H4zM8 7V5h8v2M10 13h4",
  risk: "M12 4l8 4v5c0 4-3 6-8 7-5-1-8-3-8-7V8zM12 9v4M12 16h.01",
  journal: "M6 4h12v16H6zM9 8h6M9 12h6M9 16h4",
  settings: "M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM19 12a7 7 0 0 0-.1-1l2-1.5-2-3.5-2.3.9a7 7 0 0 0-1.7-1L14.5 3h-5l-.4 2.9a7 7 0 0 0-1.7 1L5.1 6 3 9.5 5.1 11a7 7 0 0 0 0 2L3 14.5 5.1 18l2.3-.9a7 7 0 0 0 1.7-1l.4 2.9h5l.4-2.9a7 7 0 0 0 1.7-1l2.3.9 2-3.5-2-1.5c.1-.3.1-.7.1-1z",
};

const navItems = [
  ["Overview", "overview"],
  ["Scanner", "scanner"],
  ["Option Chain", "chain"],
  ["Backtests", "backtests"],
  ["Paper Trading", "paper"],
  ["Portfolio", "portfolio"],
  ["Risk", "risk"],
  ["Trade Journal", "journal"],
] as const;

const emptyDataStatus: DataStatus = {
  provider: "none",
  status: "not_loaded",
  configured: false,
  source: null,
  quote_timestamp: null,
  message: "Connect the API to load runtime data.",
};

const emptyDashboard: Dashboard = {
  mode: "PAPER",
  demo: false,
  data_status: emptyDataStatus,
  broker_status: { etrade: "disconnected", robinhood: "live unavailable" },
  live_enabled: false,
  account: { equity: 0, daily_pnl: 0, buying_power: 0, open_risk: 0, portfolio_delta: 0, portfolio_vega: 0, cash: 0, drawdown: 0 },
  equity_curve: [],
  risk_limits: [],
  candidates: [],
  recent_activity: [],
  model_health: { status: "Unavailable", signal_win_rate: null, average_trade_expectancy: null, sharpe: null, max_drawdown: null, trades_analyzed: 0, note: "Connect the API before reading model health." },
  paper: { emergency_stop: false, positions: [], orders: [] },
};

class ApiError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBase}${path}`, init);
  } catch {
    throw new ApiError("API is unreachable. Start the backend on http://127.0.0.1:8000.");
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Keep the status-based message when the server did not return JSON.
    }
    throw new ApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

function Icon({ name, size = 17 }: { name: string; size?: number }) {
  return <svg aria-hidden="true" className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none"><path d={iconPaths[name] ?? iconPaths.overview} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

function formatMoney(value: number | null | undefined, digits = 0) {
  if (value == null || !Number.isFinite(value)) return "—";
  return value.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function formatPct(value: number | null | undefined, digits = 1) {
  if (value == null || !Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function StatusTag({ children, tone = "neutral" }: { children: React.ReactNode; tone?: string }) {
  return <span className={`status-tag ${tone}`}>{children}</span>;
}

function EmptyState({ title, detail, action }: { title: string; detail: string; action?: React.ReactNode }) {
  return <div className="empty-state"><div className="empty-state-icon">∅</div><h3>{title}</h3><p>{detail}</p>{action}</div>;
}

function MetricCard({ label, value, detail, tone = "neutral" }: { label: string; value: string; detail: string; tone?: string }) {
  return <div className={`metric-card ${tone}`}><div className="metric-label">{label}<span className="info-dot">i</span></div><div className="metric-value">{value}</div><div className="metric-detail">{detail}</div></div>;
}

function EquityChart({ points }: { points: EquityPoint[] }) {
  if (points.length < 2) return <EmptyState title="No equity history" detail="Paper snapshots will appear after the account records activity." />;
  const values = points.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(max - min, 1);
  const coords = values.map((value, i) => `${(i / Math.max(values.length - 1, 1)) * 100},${92 - ((value - min) / range) * 78}`).join(" ");
  return <div className="chart-wrap"><svg className="equity-chart" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Paper equity curve"><polyline points={coords} fill="none" stroke="#85e3b1" strokeWidth="0.9" vectorEffect="non-scaling-stroke" /></svg><div className="chart-axis"><span>{formatMoney(min)}</span><span>{formatMoney(max)}</span></div></div>;
}

function ConnectionBanner({ apiConnected, error, dataStatus }: { apiConnected: boolean; error: string; dataStatus: DataStatus }) {
  if (!apiConnected) return <div className="connection-banner error"><span className="status-dot red" /><div><strong>Backend disconnected.</strong><span>{error || "Start the API, then refresh."}</span></div></div>;
  if (!dataStatus.configured) return <div className="connection-banner warning"><span className="status-dot amber" /><div><strong>No market-data provider configured.</strong><span>{dataStatus.message}</span></div></div>;
  return <div className="connection-banner success"><span className="status-dot green" /><div><strong>Market-data provider configured.</strong><span>Quotes are loaded only when you request them. Source: {dataStatus.provider}.</span></div></div>;
}

function RiskList({ limits }: { limits: RiskLimit[] }) {
  if (!limits.length) return <EmptyState title="Risk snapshot unavailable" detail="Risk limits load from the backend configuration." />;
  return <div className="risk-list">{limits.map((limit) => <div className="risk-item" key={limit.label}><div className="risk-label"><span>{limit.label}</span><strong>{Math.round(limit.used * 100)}%</strong></div><div className="progress-track"><div className={`progress-fill ${limit.used > 0.75 ? "amber-fill" : ""}`} style={{ width: `${Math.min(100, limit.used * 100)}%` }} /></div><div className="risk-limit-detail">Limit {formatMoney(limit.value, 2)}</div></div>)}</div>;
}

function ActivityList({ entries }: { entries: Dashboard["recent_activity"] }) {
  if (!entries.length) return <EmptyState title="No paper activity" detail="Submitted paper orders will appear here with their status and timestamps." />;
  return <div className="activity-list">{entries.map((activity, index) => <div className="activity-item" key={`${activity.time}-${activity.symbol}-${index}`}><div className="activity-symbol">{activity.symbol.slice(0, 1)}</div><div className="activity-copy"><strong>{activity.symbol} · {activity.action}</strong><span>{activity.details}</span></div><div className="activity-status"><StatusTag tone={activity.status === "FILLED" ? "watch" : "neutral"}>{activity.status}</StatusTag><small>{formatDateTime(activity.time)}</small></div></div>)}</div>;
}

function CandidateTable({ candidates, onSelect }: { candidates: Candidate[]; onSelect: (candidate: Candidate) => void }) {
  if (!candidates.length) return <EmptyState title="No qualified opportunities" detail="The scanner does not invent candidates. Connect a provider and run an explicit scan with validated inputs." />;
  return <div className="table-scroll"><table><thead><tr><th>UNDERLYING</th><th>STRUCTURE</th><th>EXPIRY</th><th>DEBIT</th><th>PROB. PROFIT</th><th>NET EV</th><th>RISK / REWARD</th><th>STATUS</th></tr></thead><tbody>{candidates.map((candidate) => <tr key={candidate.candidate_id} onClick={() => onSelect(candidate)}><td><strong>{candidate.underlying}</strong><span className="table-sub">{candidate.dte} DTE</span></td><td><strong>{candidate.strategy}</strong><span className="table-sub">{candidate.legs.map((leg) => `${leg.action === "BUY_OPEN" ? "L" : "S"} ${leg.strike}`).join(" / ")}</span></td><td>{candidate.expiration}</td><td>{formatMoney(candidate.ask, 2)}<span className="table-sub">{formatPct(candidate.spread_pct)} spread</span></td><td>{formatPct(candidate.probability_profit)}<span className="table-sub">{formatPct(candidate.probability_interval[0])}–{formatPct(candidate.probability_interval[1])}</span></td><td className={candidate.net_ev >= 0 ? "positive-text" : "negative-text"}>{formatMoney(candidate.net_ev, 2)}<span className="table-sub">{formatPct(candidate.risk_adjusted_edge)}</span></td><td>{formatMoney(candidate.max_profit)} / {formatMoney(candidate.max_loss)}</td><td><StatusTag tone={candidate.net_ev >= 0 ? "watch" : "pass"}>{candidate.status}</StatusTag></td></tr>)}</tbody></table></div>;
}

function Overview({ dashboard, onNavigate, onSelect }: { dashboard: Dashboard; onNavigate: (page: string) => void; onSelect: (candidate: Candidate) => void }) {
  const { account } = dashboard;
  return <><div className="page-head"><div><div className="eyebrow">RESEARCH WORKSTATION <span className="demo-badge">NO FABRICATED DATA</span></div><h1>Quantitative options research</h1><p>Measure edge after costs. Preserve capital when the evidence is weak.</p></div><div className="head-actions"><button className="secondary-button" onClick={() => onNavigate("Backtests")}><Icon name="backtests" size={15} />Backtests</button><button className="stop-button" onClick={() => onNavigate("Paper Trading")}><span className="stop-icon">■</span>{dashboard.paper.emergency_stop ? "Stop active" : "Paper controls"}</button></div></div><section className="metric-grid"><MetricCard label="Paper equity" value={formatMoney(account.equity, 2)} detail="Backend account state" tone="positive" /><MetricCard label="Paper P&L" value={formatMoney(account.daily_pnl, 2)} detail="Since paper reset" tone={account.daily_pnl < 0 ? "warning" : "positive"} /><MetricCard label="Buying power" value={formatMoney(account.buying_power, 2)} detail="Cash available" /><MetricCard label="Open risk" value={formatMoney(account.open_risk, 2)} detail="Marked paper positions" tone="warning" /><MetricCard label="Portfolio delta" value={account.portfolio_delta.toFixed(1)} detail="Only marked positions" /><MetricCard label="Portfolio vega" value={account.portfolio_vega.toFixed(1)} detail="Only marked positions" /></section><section className="split-grid main-panels"><div className="panel equity-panel"><div className="panel-head"><div><h2>Paper equity curve</h2><div className="panel-sub">Stored paper account snapshots, not a sample period</div></div></div><EquityChart points={dashboard.equity_curve} /></div><div className="panel risk-panel"><div className="panel-head"><div><h2>Risk utilization</h2><div className="panel-sub">Current vs configured limits</div></div><button className="text-button" onClick={() => onNavigate("Risk")}>View risk <span>→</span></button></div><RiskList limits={dashboard.risk_limits} /><div className="risk-foot"><span className={`status-dot ${dashboard.paper.emergency_stop ? "red" : "green"}`} />{dashboard.paper.emergency_stop ? "Paper emergency stop active" : "No recorded hard-limit breach"}</div></div></section><section className="panel candidates-panel"><div className="panel-head candidates-head"><div><h2>Research candidates</h2><div className="panel-sub">Only candidates returned by an explicit data-backed scan appear here</div></div><button className="text-button" onClick={() => onNavigate("Scanner")}>Open scanner <span>→</span></button></div><CandidateTable candidates={dashboard.candidates} onSelect={onSelect} /></section><section className="bottom-grid"><div className="panel activity-panel"><div className="panel-head"><div><h2>Recent activity</h2><div className="panel-sub">Paper account audit trail</div></div><button className="text-button" onClick={() => onNavigate("Trade Journal")}>View journal <span>→</span></button></div><ActivityList entries={dashboard.recent_activity} /></div><div className="panel health-panel"><div className="panel-head"><div><h2>Model health</h2><div className="panel-sub">Validated runs only</div></div><StatusTag tone="research">{dashboard.model_health.status}</StatusTag></div><div className="health-metrics"><div><span>Signal win rate</span><strong>{formatPct(dashboard.model_health.signal_win_rate)}</strong></div><div><span>Avg. expectancy</span><strong>{formatMoney(dashboard.model_health.average_trade_expectancy)}</strong></div><div><span>Sharpe</span><strong>{dashboard.model_health.sharpe == null ? "—" : dashboard.model_health.sharpe.toFixed(2)}</strong></div><div><span>Max drawdown</span><strong className="negative-text">{formatPct(dashboard.model_health.max_drawdown)}</strong></div></div><div className="health-note"><span className="status-dot amber" />{dashboard.model_health.note}</div></div></section></>;
}

function ScannerPage({ dashboard, onSelect }: { dashboard: Dashboard; onSelect: (candidate: Candidate) => void }) {
  const [symbol, setSymbol] = useState("");
  const [result, setResult] = useState<{ status: string; candidates: Candidate[]; message: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function runScan() { setBusy(true); setError(""); try { setResult(await apiFetch(`/api/scanner${symbol.trim() ? `?symbol=${encodeURIComponent(symbol.trim())}` : ""}`)); } catch (reason) { setError(reason instanceof Error ? reason.message : "Scanner request failed."); } finally { setBusy(false); } }
  const candidates = result?.candidates ?? dashboard.candidates;
  return <PageFrame title="Scanner" subtitle="Run explicit scans against a configured, authorized provider."><div className="panel form-panel"><div className="form-row"><label>Underlying symbol<input value={symbol} onChange={(event) => setSymbol(event.target.value.toUpperCase())} placeholder="SPY" maxLength={12} /></label><button className="primary-button" onClick={() => void runScan()} disabled={busy}>{busy ? "Checking…" : "Run scan"}</button></div><p className="form-help">The scanner refuses to rank opportunities when quote, volatility, liquidity, or historical inputs are unavailable.</p>{error && <div className="inline-error">{error}</div>}{result && <div className={`result-banner ${result.status === "ready" ? "success" : "warning"}`}><strong>{result.status === "ready" ? "Scan ready" : "No scan data"}</strong><span>{result.message}</span></div>}</div><div className="panel"><div className="panel-head"><div><h2>Candidate results</h2><div className="panel-sub">No result is treated as a trading signal</div></div></div><CandidateTable candidates={candidates} onSelect={onSelect} /></div></PageFrame>;
}

function OptionChainPage() {
  const [symbol, setSymbol] = useState("");
  const [expiration, setExpiration] = useState("");
  const [contracts, setContracts] = useState<ChainContract[]>([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function loadChain() { if (!symbol.trim() || !expiration) { setError("Enter a symbol and expiration date."); return; } setBusy(true); setError(""); setStatus(""); try { const payload = await apiFetch<{ contracts: ChainContract[]; source: string }>(`/api/market/option-chain?symbol=${encodeURIComponent(symbol.trim())}&expiration=${expiration}`); setContracts(payload.contracts); setStatus(`${payload.contracts.length} contracts returned from ${payload.source}.`); } catch (reason) { setContracts([]); setError(reason instanceof Error ? reason.message : "Option-chain request failed."); } finally { setBusy(false); } }
  return <PageFrame title="Option chain" subtitle="Inspect executable quotes, liquidity, Greeks, and provenance."><div className="panel form-panel"><div className="form-row chain-form"><label>Symbol<input value={symbol} onChange={(event) => setSymbol(event.target.value.toUpperCase())} placeholder="SPY" maxLength={12} /></label><label>Expiration<input type="date" value={expiration} onChange={(event) => setExpiration(event.target.value)} /></label><button className="primary-button" onClick={() => void loadChain()} disabled={busy}>{busy ? "Loading…" : "Load chain"}</button></div><p className="form-help">Quotes are never synthesized. A configured E*TRADE provider is required for this request.</p>{error && <div className="inline-error">{error}</div>}{status && <div className="result-banner success">{status}</div>}</div><div className="panel"><div className="panel-head"><div><h2>{symbol || "Option chain"}</h2><div className="panel-sub">Calls and puts returned by the selected provider</div></div></div>{contracts.length ? <div className="table-scroll"><table><thead><tr><th>TYPE</th><th>STRIKE</th><th>BID</th><th>ASK</th><th>MID</th><th>VOLUME</th><th>OPEN INTEREST</th><th>IV</th><th>DELTA</th><th>GAMMA</th><th>THETA</th><th>VEGA</th></tr></thead><tbody>{contracts.map((contract) => <tr key={contract.option_symbol}><td><StatusTag tone={contract.option_type === "CALL" ? "watch" : "pass"}>{contract.option_type}</StatusTag></td><td>{contract.strike.toFixed(2)}</td><td>{formatMoney(contract.bid, 2)}</td><td>{formatMoney(contract.ask, 2)}</td><td>{formatMoney((contract.bid + contract.ask) / 2, 2)}</td><td>{contract.volume.toLocaleString()}</td><td>{contract.open_interest.toLocaleString()}</td><td>{formatPct(contract.implied_volatility)}</td><td>{contract.delta?.toFixed(3) ?? "—"}</td><td>{contract.gamma?.toFixed(4) ?? "—"}</td><td>{contract.theta?.toFixed(3) ?? "—"}</td><td>{contract.vega?.toFixed(3) ?? "—"}</td></tr>)}</tbody></table></div> : <EmptyState title="No chain loaded" detail="Enter a symbol and expiration, then load data from the configured provider." />}</div></PageFrame>;
}

function PositionTable({ positions }: { positions: PaperPosition[] }) { if (!positions.length) return <EmptyState title="No open positions" detail="Filled paper orders will create positions here." />; return <div className="table-scroll"><table><thead><tr><th>SYMBOL</th><th>QUANTITY</th><th>AVERAGE PRICE</th><th>MULTIPLIER</th></tr></thead><tbody>{positions.map((position) => <tr key={position.symbol}><td>{position.symbol}</td><td>{position.quantity}</td><td>{formatMoney(position.average_price, 2)}</td><td>{position.multiplier}</td></tr>)}</tbody></table></div>; }

function OrderTable({ orders }: { orders: PaperOrder[] }) { if (!orders.length) return <EmptyState title="No orders" detail="Paper orders submitted through the API will be recorded here." />; return <div className="table-scroll"><table><thead><tr><th>TIME</th><th>SYMBOL</th><th>ACTION</th><th>QTY</th><th>LIMIT</th><th>STATUS</th><th>FILL</th></tr></thead><tbody>{orders.slice().reverse().map((order) => <tr key={order.order_id}><td>{formatDateTime(order.submitted_at)}</td><td>{order.symbol}</td><td>{order.action}</td><td>{order.filled_quantity}/{order.quantity}</td><td>{formatMoney(order.limit_price, 2)}</td><td><StatusTag tone={order.status === "FILLED" ? "watch" : order.status === "REJECTED" ? "negative" : "neutral"}>{order.status}</StatusTag></td><td>{order.fill ? formatMoney(order.fill.price, 2) : order.reason || "—"}</td></tr>)}</tbody></table></div>; }

function PortfolioPage({ dashboard }: { dashboard: Dashboard }) { return <PageFrame title="Portfolio" subtitle="Positions, capital, and Greeks from the paper broker state."><section className="metric-grid compact-metrics"><MetricCard label="Equity" value={formatMoney(dashboard.account.equity, 2)} detail="Paper account" /><MetricCard label="Cash" value={formatMoney(dashboard.account.cash, 2)} detail="Unallocated" /><MetricCard label="Open risk" value={formatMoney(dashboard.account.open_risk, 2)} detail="Defined position marks" tone="warning" /><MetricCard label="Delta" value={dashboard.account.portfolio_delta.toFixed(1)} detail="Requires Greeks" /></section><div className="panel"><div className="panel-head"><div><h2>Open positions</h2><div className="panel-sub">No position is marked with invented market prices</div></div></div><PositionTable positions={dashboard.paper.positions} /></div></PageFrame>; }

function RiskPage({ dashboard }: { dashboard: Dashboard }) { return <PageFrame title="Risk" subtitle="Hard limits are deterministic. Missing data is a reason to stop, not a reason to guess."><div className="split-grid page-grid"><div className="panel"><div className="panel-head"><div><h2>Configured limits</h2><div className="panel-sub">Conservative utilization from the in-process paper account</div></div></div><RiskList limits={dashboard.risk_limits} /></div><div className="panel"><div className="panel-head"><div><h2>Risk posture</h2><div className="panel-sub">Execution gate</div></div><StatusTag tone={dashboard.paper.emergency_stop ? "negative" : "watch"}>{dashboard.paper.emergency_stop ? "STOP ACTIVE" : "NO BREACH RECORDED"}</StatusTag></div><div className="risk-copy"><p>Live trading remains disabled by configuration and the human approval UI is not enabled.</p><p>Daily and weekly loss utilization is measured conservatively since the paper process started; persistent calendar rollups are not claimed.</p><p>Portfolio Greeks are zero until positions have validated Greek marks. This is intentionally conservative.</p></div></div></div></PageFrame>; }

function JournalPage({ dashboard }: { dashboard: Dashboard }) { return <PageFrame title="Trade journal" subtitle="Every paper order is shown with its status, fill, and reason."><div className="panel"><div className="panel-head"><div><h2>Order events</h2><div className="panel-sub">No live fills are represented here</div></div></div><OrderTable orders={dashboard.paper.orders} /></div></PageFrame>; }

function BacktestsPage() {
  const [runs, setRuns] = useState<unknown[]>([]);
  const [message, setMessage] = useState("Loading recorded runs…");
  useEffect(() => { void apiFetch<{ runs: unknown[]; message: string }>("/api/backtests").then((payload) => { setRuns(payload.runs); setMessage(payload.message); }).catch((reason) => setMessage(reason instanceof Error ? reason.message : "Backtest history unavailable.")); }, []);
  return <PageFrame title="Backtests" subtitle="Point-in-time data, realistic fills, and out-of-sample validation are required."><div className="panel"><div className="panel-head"><div><h2>Recorded experiments</h2><div className="panel-sub">{runs.length ? `${runs.length} run(s)` : "No runs"}</div></div><StatusTag tone="research">Research only</StatusTag></div><EmptyState title="No backtest runs recorded" detail={message} action={<button className="secondary-button" onClick={() => window.open("https://github.com/coopermsick-67/etrade-options-quant-lab/blob/main/docs/BACKTESTING_METHODOLOGY.md", "_blank")}>Read methodology</button>} /></div></PageFrame>;
}

function SettingsPage({ settings }: { settings: PublicSettings | null }) { return <PageFrame title="Settings" subtitle="Configuration is server-side. Secrets never enter the frontend."><div className="settings-grid"><div className="panel"><div className="panel-head"><div><h2>Runtime</h2><div className="panel-sub">Non-secret configuration</div></div></div><dl className="settings-list"><div><dt>Trading mode</dt><dd>{settings?.mode ?? "—"}</dd></div><div><dt>Market-data provider</dt><dd>{settings?.market_data_provider ?? "—"}</dd></div><div><dt>E*TRADE environment</dt><dd>{settings?.etrade_environment ?? "—"}</dd></div><div><dt>Live execution</dt><dd><StatusTag tone="negative">Disabled</StatusTag></dd></div></dl></div><div className="panel"><div className="panel-head"><div><h2>Safety boundary</h2><div className="panel-sub">Why the app may show empty states</div></div></div><div className="risk-copy"><p>No provider means no quotes, chains, IV, candidates, or fake performance.</p><p>Production execution requires an authenticated human approval UI, immutable ticket binding, broker preview, and a separate confirmation. Those controls are not bypassed from this browser.</p></div></div></div><div className="panel setup-panel"><h2>Local setup</h2><pre>{"# terminal 1\nuv run python -m apps.api.main\n\n# terminal 2\ncd apps/web\nnpm run dev"}</pre></div></PageFrame>; }

function CandidateDrawer({ candidate, onClose }: { candidate: Candidate; onClose: () => void }) { return <div className="drawer-backdrop" onClick={onClose}><aside className="candidate-drawer" onClick={(event) => event.stopPropagation()}><div className="drawer-head"><div><div className="eyebrow">CANDIDATE DETAIL</div><h2>{candidate.underlying} <span className="drawer-muted">/ {candidate.strategy}</span></h2></div><button className="close-button" onClick={onClose} aria-label="Close candidate">×</button></div><div className="drawer-status"><StatusTag tone={candidate.net_ev >= 0 ? "watch" : "pass"}>{candidate.status}</StatusTag><span>Research candidate · no live order</span></div><div className="drawer-grid"><div><span>Executable debit</span><strong>{formatMoney(candidate.ask, 2)}</strong></div><div><span>Probability of profit</span><strong>{formatPct(candidate.probability_profit)}</strong></div><div><span>Net EV</span><strong className={candidate.net_ev >= 0 ? "positive-text" : "negative-text"}>{formatMoney(candidate.net_ev, 2)}</strong></div><div><span>Risk / reward</span><strong>{formatMoney(candidate.max_loss)} / {formatMoney(candidate.max_profit)}</strong></div></div><div className="drawer-section"><h3>Legs</h3>{candidate.legs.map((leg) => <div className="leg-row" key={`${leg.action}-${leg.strike}`}><span className={leg.action === "BUY_OPEN" ? "leg-buy" : "leg-sell"}>{leg.action === "BUY_OPEN" ? "BUY" : "SELL"}</span><strong>{leg.option_type} {leg.strike}</strong><span>{formatMoney(leg.price, 2)}</span></div>)}</div><div className="drawer-section"><h3>Model inputs</h3><div className="input-grid"><div><span>IV</span><strong>{formatPct(candidate.implied_volatility)}</strong></div><div><span>Realized vol</span><strong>{formatPct(candidate.realized_volatility)}</strong></div><div><span>Forecast vol</span><strong>{formatPct(candidate.forecast_volatility)}</strong></div><div><span>Delta</span><strong>{candidate.delta.toFixed(3)}</strong></div><div><span>Gamma</span><strong>{candidate.gamma.toFixed(4)}</strong></div><div><span>Theta</span><strong>{candidate.theta.toFixed(2)}</strong></div><div><span>Vega</span><strong>{candidate.vega.toFixed(2)}</strong></div></div></div><div className="drawer-section"><h3>Assumptions and risks</h3><ul>{candidate.assumptions.map((assumption) => <li key={assumption}>{assumption}</li>)}</ul></div></aside></div>; }

function PaperTradingPage({ dashboard, refresh, apiConnected }: { dashboard: Dashboard; refresh: () => Promise<void>; apiConnected: boolean }) {
  const [form, setForm] = useState({ symbol: "", action: "BUY", quantity: "1", limit_price: "", bid: "", ask: "", multiplier: "100" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [stopBusy, setStopBusy] = useState(false);
  async function submitOrder(event: React.FormEvent) { event.preventDefault(); setBusy(true); setError(""); setMessage(""); try { const order = await apiFetch<PaperOrder>("/api/paper/orders", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ symbol: form.symbol, action: form.action, quantity: Number(form.quantity), limit_price: Number(form.limit_price), bid: Number(form.bid), ask: Number(form.ask), multiplier: Number(form.multiplier) }) }); setMessage(`Order ${order.order_id} returned ${order.status}${order.reason ? `: ${order.reason}` : "."}`); await refresh(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Paper order failed."); } finally { setBusy(false); } }
  async function toggleEmergencyStop() { setStopBusy(true); setError(""); try { await apiFetch("/api/paper/emergency-stop", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled: !dashboard.paper.emergency_stop }) }); await refresh(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Emergency-stop request failed."); } finally { setStopBusy(false); } }
  const stop = dashboard.paper.emergency_stop;
  return <PageFrame title="Paper trading" subtitle="Simulated execution only, using the quote and fill inputs you provide."><div className="paper-status"><span className={`status-dot ${stop ? "red" : "green"}`} /><strong>{stop ? "Emergency stop active" : "Paper broker ready"}</strong><span>{apiConnected ? "State is held by the backend process." : "Backend unavailable."}</span><button className="secondary-button" onClick={() => void toggleEmergencyStop()} disabled={stopBusy || !apiConnected}>{stopBusy ? "Updating…" : stop ? "Release paper stop" : "Activate emergency stop"}</button></div><div className="split-grid page-grid"><form className="panel form-panel" onSubmit={(event) => void submitOrder(event)}><div className="panel-head"><div><h2>Submit paper limit order</h2><div className="panel-sub">No live broker route exists from this form</div></div></div><div className="field-grid"><label>Contract symbol<input required value={form.symbol} onChange={(event) => setForm({ ...form, symbol: event.target.value })} placeholder="SPY-2026-12-18-C-600" /></label><label>Action<select value={form.action} onChange={(event) => setForm({ ...form, action: event.target.value })}><option>BUY</option><option>SELL</option></select></label><label>Quantity<input required type="number" min="1" max="100" value={form.quantity} onChange={(event) => setForm({ ...form, quantity: event.target.value })} /></label><label>Limit price<input required type="number" min="0.01" step="0.01" value={form.limit_price} onChange={(event) => setForm({ ...form, limit_price: event.target.value })} /></label><label>Bid<input required type="number" min="0" step="0.01" value={form.bid} onChange={(event) => setForm({ ...form, bid: event.target.value })} /></label><label>Ask<input required type="number" min="0.01" step="0.01" value={form.ask} onChange={(event) => setForm({ ...form, ask: event.target.value })} /></label><label>Multiplier<input required type="number" min="1" step="1" value={form.multiplier} onChange={(event) => setForm({ ...form, multiplier: event.target.value })} /></label></div><button className="primary-button wide-button" type="submit" disabled={busy || stop || !apiConnected}>{busy ? "Submitting…" : stop ? "Blocked by emergency stop" : "Submit paper order"}</button>{message && <div className="result-banner success">{message}</div>}{error && <div className="inline-error">{error}</div>}<p className="form-help">Buying uses the ask plus configured slippage. Selling requires an existing paper position unless uncovered shorts are explicitly enabled in code.</p></form><div className="panel"><div className="panel-head"><div><h2>Account state</h2><div className="panel-sub">Current backend snapshot</div></div></div><div className="account-summary"><div><span>Equity</span><strong>{formatMoney(dashboard.account.equity, 2)}</strong></div><div><span>Cash</span><strong>{formatMoney(dashboard.account.cash, 2)}</strong></div><div><span>Buying power</span><strong>{formatMoney(dashboard.account.buying_power, 2)}</strong></div><div><span>Open risk</span><strong>{formatMoney(dashboard.account.open_risk, 2)}</strong></div></div><h3 className="subheading">Positions</h3><PositionTable positions={dashboard.paper.positions} /></div></div><div className="panel"><div className="panel-head"><div><h2>Orders</h2><div className="panel-sub">Idempotent paper order records</div></div></div><OrderTable orders={dashboard.paper.orders} /></div></PageFrame>;
}

function PageFrame({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) { return <><div className="page-head compact-head"><div><div className="eyebrow">WORKSPACE</div><h1>{title}</h1><p>{subtitle}</p></div></div><div className="page-content">{children}</div></>; }

function App() {
  const [dashboard, setDashboard] = useState<Dashboard>(emptyDashboard);
  const [activeNav, setActiveNav] = useState("Overview");
  const [selected, setSelected] = useState<Candidate | null>(null);
  const [loading, setLoading] = useState(true);
  const [apiConnected, setApiConnected] = useState(false);
  const [error, setError] = useState("");
  const [noticeDismissed, setNoticeDismissed] = useState(false);
  const [settings, setSettings] = useState<PublicSettings | null>(null);

  const refreshDashboard = useCallback(async () => { setLoading(true); try { const [nextDashboard, stop] = await Promise.all([apiFetch<Dashboard>("/api/dashboard"), apiFetch<{ enabled: boolean }>("/api/paper/emergency-stop")]); setDashboard({ ...nextDashboard, paper: { ...nextDashboard.paper, emergency_stop: stop.enabled } }); setApiConnected(true); setError(""); } catch (reason) { setApiConnected(false); setError(reason instanceof Error ? reason.message : "Backend request failed."); } finally { setLoading(false); } }, []);
  useEffect(() => { void refreshDashboard(); }, [refreshDashboard]);
  useEffect(() => { void apiFetch<PublicSettings>("/api/settings/public").then(setSettings).catch(() => undefined); }, []);
  const dataStatus = apiConnected ? dashboard.data_status : emptyDataStatus;
  const activeIcon = navItems.find(([label]) => label === activeNav)?.[1] ?? "overview";
  function renderPage() { if (activeNav === "Overview") return <Overview dashboard={dashboard} onNavigate={setActiveNav} onSelect={setSelected} />; if (activeNav === "Scanner") return <ScannerPage dashboard={dashboard} onSelect={setSelected} />; if (activeNav === "Option Chain") return <OptionChainPage />; if (activeNav === "Backtests") return <BacktestsPage />; if (activeNav === "Paper Trading") return <PaperTradingPage dashboard={dashboard} refresh={refreshDashboard} apiConnected={apiConnected} />; if (activeNav === "Portfolio") return <PortfolioPage dashboard={dashboard} />; if (activeNav === "Risk") return <RiskPage dashboard={dashboard} />; if (activeNav === "Trade Journal") return <JournalPage dashboard={dashboard} />; return <SettingsPage settings={settings} />; }
  return <div className="app-shell"><aside className="sidebar"><div className="brand"><div className="brand-mark">Q</div><div><div className="brand-name">QUANT LAB</div><div className="brand-sub">Options research</div></div></div><div className="nav-group-label">WORKSPACE</div><nav aria-label="Workspace navigation">{navItems.map(([label, icon]) => <button className={`nav-item ${activeNav === label ? "active" : ""}`} key={label} onClick={() => setActiveNav(label)} aria-current={activeNav === label ? "page" : undefined}><Icon name={icon} /><span>{label}</span>{label === "Risk" && dashboard.risk_limits.some((limit) => limit.used >= 1) && <span className="nav-count">!</span>}</button>)}</nav><div className="sidebar-spacer" /><div className="nav-group-label">SYSTEM</div><button className={`nav-item ${activeNav === "Settings" ? "active" : ""}`} onClick={() => setActiveNav("Settings")}><Icon name="settings" /><span>Settings</span></button><div className="health-card"><div className="health-title"><span className={`status-dot ${apiConnected ? "green" : "red"}`} />System health</div><div className="health-row"><span>API</span><strong>{apiConnected ? "Connected" : "Offline"}</strong></div><div className="health-row"><span>Data provider</span><strong>{dataStatus.provider}</strong></div><div className="health-row"><span>Mode</span><strong className="mint">{dashboard.mode}</strong></div></div><div className="user-row"><div className="avatar">QL</div><div><div className="user-name">Local workspace</div><div className="user-role">No broker credentials in browser</div></div></div></aside><main className="main-content"><header className="topbar"><div className="breadcrumb"><span className="muted">Workspace</span><span>/</span><strong><Icon name={activeIcon} size={13} /> {activeNav}</strong></div><div className="top-actions"><div className="mode-pill"><span className="status-dot mint-dot" />{dashboard.mode}</div><div className="broker-pill"><span className={`status-dot ${dataStatus.configured ? "green" : "amber"}`} />E*TRADE <span className="muted">{dashboard.broker_status.etrade}</span></div><div className="broker-pill"><span className="status-dot red" />Robinhood <span className="muted">unavailable</span></div><button className="icon-button" aria-label="Refresh dashboard" onClick={() => void refreshDashboard()}>{loading ? "…" : "↻"}</button></div></header><div className="content-wrap"><ConnectionBanner apiConnected={apiConnected} error={error} dataStatus={dataStatus} />{!noticeDismissed && <div className="notice-bar"><div className="notice-icon">i</div><div><strong>Fail-closed research mode.</strong> Empty states mean required data is absent. No quotes, Greeks, candidates, or performance are fabricated.</div><button aria-label="Dismiss notice" onClick={() => setNoticeDismissed(true)}>×</button></div>}{renderPage()}<footer className="footer-note"><span>Quant Lab v0.1.0</span><span>{loading ? "Refreshing…" : "State refreshed"}</span><span>Deterministic calculations · source timestamps required</span><span className="footer-right"><span className={`status-dot ${apiConnected ? "green" : "red"}`} />{apiConnected ? "API connected" : "API unavailable"}</span></footer></div></main>{selected && <CandidateDrawer candidate={selected} onClose={() => setSelected(null)} />}</div>;
}

export default App;
