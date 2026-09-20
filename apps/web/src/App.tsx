import { useEffect, useMemo, useState } from "react";

type EquityPoint = { label: string; value: number };
type Candidate = {
  candidate_id: string;
  underlying: string;
  strategy: string;
  expiration: string;
  dte: number;
  bid: number;
  ask: number;
  midpoint: number;
  spread_pct: number;
  implied_volatility: number;
  realized_volatility: number | null;
  forecast_volatility: number;
  probability_profit: number;
  probability_interval: [number, number];
  max_loss: number;
  max_profit: number;
  gross_ev: number;
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
type Dashboard = {
  mode: string;
  demo: boolean;
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
  risk_limits: Array<{ label: string; value: number; used: number }>;
  candidates: Candidate[];
  recent_activity: Array<{ time: string; symbol: string; action: string; details: string; status: string }>;
  model_health: {
    status: string;
    signal_win_rate: number;
    average_trade_expectancy: number;
    sharpe: number;
    max_drawdown: number;
    trades_analyzed: number;
    note: string;
  };
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
  settings: "M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM19 12a7 7 0 0 0-.1-1l2-1.5-2-3.5-2.3.9a7 7 0 0 0-1.7-1L14.5 3h-5l-.4 2.9a7 7 0 0 0-1.7 1L5.1 6 3 9.5 5.1 11a7 7 0 0 0 0 2L3 14.5 5.1 18l2.3-.9a7 7 0 0 0 1.7 1l.4 2.9h5l.4-2.9a7 7 0 0 0 1.7-1l2.3.9 2-3.5-2-1.5c.1-.3.1-.7.1-1z",
};

function Icon({ name, size = 17 }: { name: string; size?: number }) {
  return (
    <svg aria-hidden="true" className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d={iconPaths[name] ?? iconPaths.overview} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function formatMoney(value: number, digits = 0) {
  return value.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function formatPct(value: number, digits = 1) {
  return `${(value * 100).toFixed(digits)}%`;
}

function fallbackDashboard(): Dashboard {
  return {
    mode: "PAPER",
    demo: true,
    broker_status: { etrade: "disconnected", robinhood: "live unavailable" },
    live_enabled: false,
    account: { equity: 10342.56, daily_pnl: 121.18, buying_power: 8451.22, open_risk: 1213, portfolio_delta: -18.4, portfolio_vega: 312.7, cash: 8451.22, drawdown: -0.012 },
    equity_curve: [10000, 10042, 10035, 10088, 10065, 10121, 10093, 10168, 10145, 10214, 10198, 10342.56].map((value, i) => ({ label: `T${i + 1}`, value })),
    risk_limits: [
      { label: "Max position size", value: 2000, used: 0.61 },
      { label: "Max portfolio delta", value: 500, used: 0.04 },
      { label: "Max portfolio vega", value: 1000, used: 0.31 },
      { label: "Daily loss limit", value: 500, used: 0.25 },
      { label: "Total drawdown limit", value: 2000, used: 0.17 },
    ],
    candidates: [],
    recent_activity: [],
    model_health: { status: "Research only", signal_win_rate: 0.542, average_trade_expectancy: 36.12, sharpe: 1.08, max_drawdown: -0.124, trades_analyzed: 2381, note: "Demo sample data. No live or out-of-sample profitability claim." },
  };
}

function EquityChart({ points }: { points: EquityPoint[] }) {
  const values = points.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(max - min, 1);
  const coords = values.map((value, i) => `${(i / Math.max(values.length - 1, 1)) * 100},${92 - ((value - min) / range) * 78}`).join(" ");
  const area = `0,92 ${coords} 100,92`;
  return (
    <div className="chart-wrap">
      <svg className="equity-chart" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Paper equity curve">
        <defs>
          <linearGradient id="area-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#78e7ae" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#78e7ae" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={`M ${area.replaceAll(" ", " L ")}`} fill="url(#area-fill)" />
        <polyline points={coords} fill="none" stroke="#85e3b1" strokeWidth="0.9" vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="chart-axis"><span>{formatMoney(min)}</span><span>{formatMoney(max)}</span></div>
    </div>
  );
}

function MetricCard({ label, value, detail, tone = "neutral" }: { label: string; value: string; detail: string; tone?: string }) {
  return <div className={`metric-card ${tone}`}><div className="metric-label">{label}<span className="info-dot">i</span></div><div className="metric-value">{value}</div><div className="metric-detail">{detail}</div></div>;
}

function App() {
  const [dashboard, setDashboard] = useState<Dashboard>(fallbackDashboard());
  const [activeNav, setActiveNav] = useState("Overview");
  const [query, setQuery] = useState("");
  const [strategyFilter, setStrategyFilter] = useState("All strategies");
  const [selected, setSelected] = useState<Candidate | null>(null);
  const [showQualifiedOnly, setShowQualifiedOnly] = useState(false);
  const [emergencyStop, setEmergencyStop] = useState(false);
  const [loading, setLoading] = useState(true);
  const [apiConnected, setApiConnected] = useState(false);
  const [noticeDismissed, setNoticeDismissed] = useState(false);
  const [paperMessage, setPaperMessage] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    let mounted = true;
    fetch(`${apiBase}/api/dashboard`, { signal: controller.signal })
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error("API unavailable"))))
      .then((payload: Dashboard) => {
        if (mounted) {
          setDashboard(payload);
          setApiConnected(true);
        }
      })
      .catch((error: unknown) => {
        if (mounted && !(error instanceof DOMException && error.name === "AbortError")) {
          setApiConnected(false);
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    fetch(`${apiBase}/api/paper/emergency-stop`, { signal: controller.signal })
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error("API unavailable"))))
      .then((payload: { enabled: boolean }) => {
        if (mounted) setEmergencyStop(payload.enabled);
      })
      .catch(() => undefined);
    return () => {
      mounted = false;
      controller.abort();
    };
  }, []);

  const strategies = useMemo(() => ["All strategies", ...new Set(dashboard.candidates.map((candidate) => candidate.strategy))], [dashboard.candidates]);
  const filteredCandidates = useMemo(() => dashboard.candidates.filter((candidate) => {
    const matchesQuery = `${candidate.underlying} ${candidate.strategy}`.toLowerCase().includes(query.toLowerCase());
    const matchesStrategy = strategyFilter === "All strategies" || candidate.strategy === strategyFilter;
    const matchesQualified = !showQualifiedOnly || candidate.net_ev > 0;
    return matchesQuery && matchesStrategy && matchesQualified;
  }), [dashboard.candidates, query, showQualifiedOnly, strategyFilter]);

  function inspectCandidate(candidate: Candidate) {
    setSelected(candidate);
    setPaperMessage("");
  }

  function runPaperAction(candidate: Candidate) {
    if (emergencyStop) {
      setPaperMessage("Emergency stop active — paper order blocked.");
      return;
    }
    setPaperMessage(`${candidate.underlying} paper ticket prepared. Review the exact debit and risk before submitting.`);
  }

  async function toggleEmergencyStop() {
    const enabled = !emergencyStop;
    setEmergencyStop(enabled);
    try {
      const response = await fetch(`${apiBase}/api/paper/emergency-stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      });
      if (!response.ok) throw new Error("emergency-stop request failed");
      const payload = (await response.json()) as { enabled: boolean };
      setEmergencyStop(payload.enabled);
    } catch {
      setPaperMessage("Backend emergency-stop state could not be confirmed; treat the stop as active until the API reconnects.");
      setEmergencyStop(true);
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">Q</div><div><div className="brand-name">QUANT LAB</div><div className="brand-sub">Options research</div></div></div>
        <div className="nav-group-label">WORKSPACE</div>
        <nav>
          {["Overview", "Scanner", "Option Chain", "Backtests", "Paper Trading", "Portfolio", "Risk", "Trade Journal"].map((item) => {
            const key = item.toLowerCase().replaceAll(" ", "");
            const icon = item === "Option Chain" ? "chain" : item === "Paper Trading" ? "paper" : item === "Trade Journal" ? "journal" : key;
            return <button className={`nav-item ${activeNav === item ? "active" : ""}`} key={item} onClick={() => setActiveNav(item)}><Icon name={icon} /><span>{item}</span>{item === "Risk" && <span className="nav-count">1</span>}</button>;
          })}
        </nav>
        <div className="sidebar-spacer" />
        <div className="nav-group-label">SYSTEM</div>
        <button className="nav-item" onClick={() => setActiveNav("Settings")}><Icon name="settings" /><span>Settings</span></button>
        <div className="health-card"><div className="health-title"><span className="status-dot green" />System health</div><div className="health-row"><span>Data provider</span><strong>Mock / demo</strong></div><div className="health-row"><span>Last quote</span><strong>2.1s ago</strong></div><div className="health-row"><span>Mode</span><strong className="mint">PAPER</strong></div></div>
        <div className="user-row"><div className="avatar">AK</div><div><div className="user-name">Research account</div><div className="user-role">Local workspace</div></div><span className="more">•••</span></div>
      </aside>

      <main className="main-content">
        <header className="topbar"><div className="breadcrumb"><span className="muted">Workspace</span><span>/</span><strong>{activeNav}</strong></div><div className="top-actions"><div className="mode-pill"><span className="status-dot mint-dot" />PAPER <span className="caret">⌄</span></div><div className="broker-pill"><span className="status-dot amber" />E*TRADE <span className="muted">disconnected</span></div><div className="broker-pill"><span className="status-dot red" />Robinhood <span className="muted">unavailable</span></div><button className="icon-button" aria-label="Notifications">◌</button><div className="top-avatar">AK</div></div></header>

        <div className="content-wrap">
          <div className="page-head"><div><div className="eyebrow">RESEARCH WORKSTATION <span className="demo-badge">{dashboard.demo ? "DEMO DATA" : "CONNECTED"}</span></div><h1>Good morning, Alex.</h1><p>Measure edge after costs. Preserve capital when the evidence is weak.</p></div><div className="head-actions"><button className="secondary-button" onClick={() => setActiveNav("Backtests")}><Icon name="backtests" size={15} />Run a backtest</button><button className={`stop-button ${emergencyStop ? "engaged" : ""}`} onClick={() => void toggleEmergencyStop()}><span className="stop-icon">■</span>{emergencyStop ? "Stop active" : "Emergency stop"}</button></div></div>

          {!noticeDismissed && <div className="notice-bar"><div className="notice-icon">i</div><div><strong>Research mode is active.</strong> Paper results are simulated and not evidence of live profitability. Robinhood live-options execution is unavailable; E*TRADE live actions require a fresh human approval.</div><button aria-label="Dismiss notice" onClick={() => setNoticeDismissed(true)}>×</button></div>}

          <section className="metric-grid"><MetricCard label="Account equity" value={formatMoney(dashboard.account.equity, 2)} detail="+$342.56 since start" tone="positive" /><MetricCard label="Today’s P&L" value={`+${formatMoney(dashboard.account.daily_pnl, 2)}`} detail="+1.18% · paper" tone="positive" /><MetricCard label="Buying power" value={formatMoney(dashboard.account.buying_power, 2)} detail="82.1% available" /><MetricCard label="Open risk" value={formatMoney(dashboard.account.open_risk)} detail="12.1% of equity" tone="warning" /><MetricCard label="Portfolio delta" value={dashboard.account.portfolio_delta.toFixed(1)} detail="Near neutral" /><MetricCard label="Portfolio vega" value={`+${dashboard.account.portfolio_vega.toFixed(1)}`} detail="+$3.13 per vol pt" /></section>

          <section className="split-grid main-panels"><div className="panel equity-panel"><div className="panel-head"><div><h2>Paper equity curve</h2><div className="panel-sub">Cumulative paper account value · sample period</div></div><div className="panel-select">Last 30 days <span>⌄</span></div></div><div className="chart-legend"><span><i className="legend-line" />Equity</span><span><i className="legend-dash" />Starting equity</span></div><EquityChart points={dashboard.equity_curve} /><div className="chart-footer"><span>Starting equity <strong>$10,000</strong></span><span>Peak <strong>$10,342.56</strong></span><span>Drawdown <strong className="mint">-1.2%</strong></span></div></div><div className="panel risk-panel"><div className="panel-head"><div><h2>Risk utilization</h2><div className="panel-sub">Current vs configured limits</div></div><button className="text-button" onClick={() => setActiveNav("Risk")}>View all <span>→</span></button></div><div className="risk-list">{dashboard.risk_limits.map((limit) => <div className="risk-item" key={limit.label}><div className="risk-label"><span>{limit.label}</span><strong>{Math.round(limit.used * 100)}%</strong></div><div className="progress-track"><div className={`progress-fill ${limit.used > 0.75 ? "amber-fill" : ""}`} style={{ width: `${Math.min(100, limit.used * 100)}%` }} /></div></div>)}</div><div className="risk-foot"><span className="status-dot green" />No hard risk limits breached <span className="info-dot">i</span></div></div></section>

          <section className="panel candidates-panel"><div className="panel-head candidates-head"><div><h2>Research candidates</h2><div className="panel-sub">Ranked by net edge after estimated costs and uncertainty</div></div><button className="text-button" onClick={() => setActiveNav("Scanner")}>Open scanner <span>→</span></button></div><div className="filter-row"><div className="search-box"><span>⌕</span><input placeholder="Search symbol or strategy" value={query} onChange={(event) => setQuery(event.target.value)} /></div><select value={strategyFilter} onChange={(event) => setStrategyFilter(event.target.value)}>{strategies.map((strategy) => <option key={strategy}>{strategy}</option>)}</select><label className="check-label"><input type="checkbox" checked={showQualifiedOnly} onChange={(event) => setShowQualifiedOnly(event.target.checked)} /> Positive net edge only</label><span className="result-count">{filteredCandidates.length} of {dashboard.candidates.length} candidates</span></div><div className="table-scroll"><table><thead><tr><th>UNDERLYING</th><th>STRUCTURE</th><th>EXPIRY</th><th>DEBIT</th><th>PROB. PROFIT</th><th>NET EV</th><th>RISK / REWARD</th><th>MODEL STATUS</th><th /></tr></thead><tbody>{filteredCandidates.length === 0 ? <tr><td colSpan={9} className="empty-cell">No qualified opportunities in the current demo set. A pass is a valid research outcome.</td></tr> : filteredCandidates.map((candidate) => <tr key={candidate.candidate_id} className={selected?.candidate_id === candidate.candidate_id ? "selected-row" : ""} onClick={() => inspectCandidate(candidate)}><td><div className="symbol-cell"><span className={`symbol-dot ${candidate.underlying.toLowerCase()}`} /> <strong>{candidate.underlying}</strong><span className="tiny-muted">{candidate.underlying === "SPY" ? "ETF" : "Equity"}</span></div></td><td><strong>{candidate.strategy.replace("Bull call spread", "Bull call spread")}</strong><span className="table-sub">{candidate.legs.map((leg) => `${leg.action === "BUY_OPEN" ? "L" : "S"} ${leg.strike}`).join(" / ")}</span></td><td><strong>{candidate.expiration}</strong><span className="table-sub">{candidate.dte} DTE</span></td><td><strong>{formatMoney(candidate.ask, 2)}</strong><span className="table-sub">{formatPct(candidate.spread_pct)} spread</span></td><td><strong>{formatPct(candidate.probability_profit)}</strong><span className="table-sub">{formatPct(candidate.probability_interval[0])}–{formatPct(candidate.probability_interval[1])} interval</span></td><td className={candidate.net_ev >= 0 ? "positive-text" : "negative-text"}><strong>{candidate.net_ev >= 0 ? "+" : ""}{formatMoney(candidate.net_ev, 2)}</strong><span className="table-sub">{formatPct(candidate.risk_adjusted_edge)}</span></td><td><strong>{formatMoney(candidate.max_profit)} / {formatMoney(candidate.max_loss)}</strong><span className="table-sub">Defined risk</span></td><td><span className={`status-tag ${candidate.net_ev >= 0 ? "watch" : "pass"}`}>{candidate.net_ev >= 0 ? "Review" : "Pass"}</span><span className="table-sub">{candidate.status}</span></td><td><button className="row-menu" onClick={(event) => { event.stopPropagation(); inspectCandidate(candidate); }}>•••</button></td></tr>)}</tbody></table></div></section>

          <section className="bottom-grid"><div className="panel activity-panel"><div className="panel-head"><div><h2>Recent activity</h2><div className="panel-sub">Paper account audit trail</div></div><button className="text-button" onClick={() => setActiveNav("Trade Journal")}>View journal <span>→</span></button></div><div className="activity-list">{dashboard.recent_activity.map((activity) => <div className="activity-item" key={`${activity.time}-${activity.symbol}`}><div className="activity-symbol">{activity.symbol.slice(0, 1)}</div><div className="activity-copy"><strong>{activity.symbol} · {activity.action}</strong><span>{activity.details}</span></div><div className="activity-status"><span className="status-dot green" />{activity.status}<small>{activity.time}</small></div></div>)}</div></div><div className="panel health-panel"><div className="panel-head"><div><h2>Model health</h2><div className="panel-sub">Validation signals · research only</div></div><span className="status-tag research">{dashboard.model_health.status}</span></div><div className="health-metrics"><div><span>Signal win rate</span><strong>{formatPct(dashboard.model_health.signal_win_rate)}</strong></div><div><span>Avg. expectancy</span><strong>{formatMoney(dashboard.model_health.average_trade_expectancy)}</strong></div><div><span>Sharpe</span><strong>{dashboard.model_health.sharpe.toFixed(2)}</strong></div><div><span>Max drawdown</span><strong className="negative-text">{formatPct(dashboard.model_health.max_drawdown)}</strong></div></div><div className="health-note"><span className="status-dot amber" />{dashboard.model_health.note}</div></div></section>

          <footer className="footer-note"><span>Quant Lab v0.1.0</span><span>Last refresh {loading ? "loading…" : "just now"}</span><span>All calculations deterministic · source timestamps required</span><span className="footer-right"><span className={`status-dot ${apiConnected ? "green" : "red"}`} />{apiConnected ? "API connected" : "API unavailable · demo fallback"}</span></footer>
        </div>
      </main>

      {selected && <div className="drawer-backdrop" onClick={() => setSelected(null)}><aside className="candidate-drawer" onClick={(event) => event.stopPropagation()}><div className="drawer-head"><div><div className="eyebrow">CANDIDATE DETAIL</div><h2>{selected.underlying} <span className="drawer-muted">/ {selected.strategy}</span></h2></div><button className="close-button" onClick={() => setSelected(null)}>×</button></div><div className="drawer-status"><span className={`status-tag ${selected.net_ev >= 0 ? "watch" : "pass"}`}>{selected.net_ev >= 0 ? "Review" : "Pass"}</span><span>Research candidate · no live order</span></div><div className="drawer-grid"><div><span>Executable debit</span><strong>{formatMoney(selected.ask, 2)}</strong></div><div><span>Probability of profit</span><strong>{formatPct(selected.probability_profit)}</strong></div><div><span>Net EV</span><strong className={selected.net_ev >= 0 ? "positive-text" : "negative-text"}>{formatMoney(selected.net_ev, 2)}</strong></div><div><span>Risk / reward</span><strong>{formatMoney(selected.max_loss)} / {formatMoney(selected.max_profit)}</strong></div></div><div className="drawer-section"><h3>Legs</h3>{selected.legs.map((leg) => <div className="leg-row" key={`${leg.action}-${leg.strike}`}><span className={leg.action === "BUY_OPEN" ? "leg-buy" : "leg-sell"}>{leg.action === "BUY_OPEN" ? "BUY" : "SELL"}</span><strong>{leg.option_type} {leg.strike}</strong><span>{formatMoney(leg.price, 2)}</span></div>)}</div><div className="drawer-section"><h3>Model inputs</h3><div className="input-grid"><div><span>IV</span><strong>{formatPct(selected.implied_volatility)}</strong></div><div><span>Realized vol</span><strong>{selected.realized_volatility == null ? "N/A" : formatPct(selected.realized_volatility)}</strong></div><div><span>Forecast vol</span><strong>{formatPct(selected.forecast_volatility ?? selected.implied_volatility)}</strong></div><div><span>Delta</span><strong>{selected.delta.toFixed(3)}</strong></div><div><span>Gamma</span><strong>{selected.gamma.toFixed(4)}</strong></div><div><span>Theta</span><strong>{selected.theta.toFixed(2)}</strong></div><div><span>Vega</span><strong>{selected.vega.toFixed(2)}</strong></div></div></div><div className="drawer-section"><h3>Why this could fail</h3><ul>{selected.assumptions.map((assumption) => <li key={assumption}>{assumption}</li>)}</ul><p className="drawer-warning">A model estimate is not certainty. Review quote age, event risk, slippage, and portfolio impact before any paper action.</p></div><div className="drawer-actions"><button className="secondary-button" onClick={() => setPaperMessage("Backtest queued with conservative, realistic, and optimistic fills.")}>Run scenario</button><button className="primary-button" onClick={() => runPaperAction(selected)} disabled={emergencyStop}>Prepare paper ticket</button></div>{paperMessage && <div className="drawer-message">{paperMessage}</div>}</aside></div>}
    </div>
  );
}

export default App;
