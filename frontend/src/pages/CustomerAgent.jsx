import { useState } from 'react'
import { runAgent } from '../services/api'

// ── helpers ───────────────────────────────────────────────────────────────────

const STATUS = {
  CRITICAL: { border: 'border-danger',  badge: 'bg-danger/20  text-danger',  section: 'text-danger'  },
  AT_RISK:  { border: 'border-warning', badge: 'bg-warning/20 text-warning', section: 'text-warning' },
  HEALTHY:  { border: 'border-success', badge: 'bg-success/20 text-success', section: 'text-success' },
}

const SEGMENT_COLORS = {
  Enterprise:  'bg-primary/20  text-primary',
  SMB:         'bg-purple-500/20 text-purple-300',
  Retail:      'bg-cyan-500/20   text-cyan-300',
  Government:  'bg-orange-500/20 text-orange-300',
}

// direction: "below" means lower is worse
const THRESHOLDS = {
  order_completion_rate: { warn: 85, crit: 70, direction: 'below' },
  avg_fulfillment_time:  { warn: 48, crit: 72, direction: 'above' },
  sla_breach_rate:       { warn:  5, crit: 15, direction: 'above' },
}

function metricLevel(value, key) {
  const t = THRESHOLDS[key]
  const v = parseFloat(value)
  if (t.direction === 'below') {
    if (v < t.crit) return 'critical'
    if (v < t.warn) return 'warning'
  } else {
    if (v > t.crit) return 'critical'
    if (v > t.warn) return 'warning'
  }
  return 'normal'
}

// ── sub-components ────────────────────────────────────────────────────────────

function MetricPill({ label, value, level }) {
  const color =
    level === 'critical' ? 'bg-danger/20  text-danger'  :
    level === 'warning'  ? 'bg-warning/20 text-warning' :
                           'bg-white/5    text-muted'
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-mono ${color}`}>
      {label}: {value}
    </span>
  )
}

function AccountCard({ report }) {
  const [open, setOpen] = useState(false)
  const st    = STATUS[report.status] ?? STATUS.HEALTHY
  const m     = report.metrics
  const alert = report.alert
  const segColor = SEGMENT_COLORS[report.segment] ?? 'bg-white/5 text-muted'

  const compLvl = metricLevel(m.order_completion_rate, 'order_completion_rate')
  const fulfLvl = metricLevel(m.avg_fulfillment_time,  'avg_fulfillment_time')
  const slaLvl  = metricLevel(m.sla_breach_rate,       'sla_breach_rate')

  return (
    <div className={`bg-panel border ${st.border} rounded-lg p-4 flex flex-col gap-3`}>
      {/* header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-mono font-bold text-white text-sm truncate">{report.name}</p>
          <p className="text-xs text-muted font-mono">{report.account_id} · {report.region}</p>
        </div>
        <span className={`shrink-0 text-xs px-2 py-0.5 rounded-full font-mono ${st.badge}`}>
          {report.status}
        </span>
      </div>

      {/* segment + plan + orders */}
      <div className="flex flex-wrap gap-1">
        <span className={`text-xs px-2 py-0.5 rounded font-mono ${segColor}`}>{report.segment}</span>
        <span className="text-xs px-2 py-0.5 rounded font-mono bg-white/5 text-muted">{report.plan}</span>
        <span className="text-xs px-2 py-0.5 rounded font-mono bg-white/5 text-muted">
          {report.active_orders} orders
        </span>
      </div>

      {/* metrics */}
      <div className="flex flex-wrap gap-1">
        <MetricPill label="Completion"  value={m.order_completion_rate} level={compLvl} />
        <MetricPill label="Fulfillment" value={m.avg_fulfillment_time}  level={fulfLvl} />
        <MetricPill label="SLA Breach"  value={m.sla_breach_rate}       level={slaLvl}  />
      </div>

      {/* alert expand */}
      {alert.raised && (
        <div>
          <button
            onClick={() => setOpen(o => !o)}
            className="text-xs font-mono text-muted hover:text-white underline"
          >
            {open ? 'Hide analysis ▲' : 'Show analysis ▼'}
          </button>
          {open && (
            <div className="mt-3 space-y-2 border-t border-slate-700 pt-3 text-xs font-mono">
              <div>
                <p className="text-muted mb-0.5">Breach</p>
                <p className="text-warning leading-relaxed">{alert.reason}</p>
              </div>
              <div>
                <p className="text-muted mb-0.5">Root Cause</p>
                <p className="text-white leading-relaxed">{alert.root_cause || '—'}</p>
              </div>
              <div>
                <p className="text-muted mb-0.5">Recommendation</p>
                <p className="text-success leading-relaxed">{alert.recommendation || '—'}</p>
              </div>
              {alert.reasoning && (
                <div>
                  <p className="text-muted mb-0.5">Reasoning</p>
                  <p className="text-slate-300 leading-relaxed">{alert.reasoning}</p>
                </div>
              )}
              <p className="text-slate-600">{alert.timestamp}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, color }) {
  return (
    <div className="bg-panel border border-slate-700 rounded-lg p-4 flex flex-col gap-1">
      <p className="text-muted text-xs font-mono uppercase tracking-wide">{label}</p>
      <p className={`text-3xl font-display font-bold ${color}`}>{value ?? '—'}</p>
    </div>
  )
}

function Section({ title, color, accounts }) {
  if (!accounts.length) return null
  return (
    <section>
      <h2 className={`text-xs font-mono uppercase tracking-widest mb-3 ${color}`}>
        {title} ({accounts.length})
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {accounts.map(r => <AccountCard key={r.account_id} report={r} />)}
      </div>
    </section>
  )
}

// ── page ──────────────────────────────────────────────────────────────────────

export default function CustomerAgent() {
  const [loading, setLoading] = useState(false)
  const [result,  setResult]  = useState(null)
  const [error,   setError]   = useState(null)

  const runScan = async () => {
    setLoading(true)
    setError(null)
    try {
      const resp = await runAgent('customer', {
        query:      'Run full customer order health scan',
        session_id: `cust-scan-${Date.now()}`,
      })
      setResult(resp.result)
    } catch (e) {
      setError(e?.response?.data?.detail ?? e.message ?? 'Scan failed')
    } finally {
      setLoading(false)
    }
  }

  const summary  = result?.summary
  const reports  = result?.customer_reports ?? []
  const critical = reports.filter(r => r.status === 'CRITICAL')
  const atRisk   = reports.filter(r => r.status === 'AT_RISK')
  const healthy  = reports.filter(r => r.status === 'HEALTHY')

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">

      {/* header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-bold text-white">Customer Order Health</h1>
          <p className="text-muted text-sm font-mono mt-1">
            10 accounts &nbsp;·&nbsp; Completion / Fulfillment Time / SLA Breach
          </p>
        </div>
        <button
          onClick={runScan}
          disabled={loading}
          className="shrink-0 px-5 py-2 bg-primary text-white rounded-lg font-mono text-sm
                     disabled:opacity-50 hover:bg-primary/80 transition-colors flex items-center gap-2"
        >
          {loading && (
            <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent
                             rounded-full animate-spin inline-block" />
          )}
          {loading ? 'Scanning…' : '▶ Run Scan'}
        </button>
      </div>

      {/* error */}
      {error && (
        <div className="bg-danger/10 border border-danger rounded-lg p-4 text-danger font-mono text-sm">
          {error}
        </div>
      )}

      {/* scanning notice */}
      {loading && (
        <p className="text-muted font-mono text-sm animate-pulse">
          Fetching account metrics → evaluating SLA thresholds → LLM root-cause analysis…
        </p>
      )}

      {/* summary cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Total Accounts" value={summary.total_accounts} color="text-white"   />
          <StatCard label="Healthy"         value={summary.healthy}        color="text-success" />
          <StatCard label="At Risk"         value={summary.at_risk}        color="text-warning" />
          <StatCard label="Critical"        value={summary.critical}       color="text-danger"  />
        </div>
      )}

      {/* account sections */}
      {reports.length > 0 && (
        <div className="space-y-8">
          <Section title="Critical" color="text-danger"  accounts={critical} />
          <Section title="At Risk"  color="text-warning" accounts={atRisk}   />
          <Section title="Healthy"  color="text-success" accounts={healthy}  />
        </div>
      )}

      {/* empty state */}
      {!loading && !result && (
        <div className="text-center py-20 text-muted font-mono text-sm">
          Press{' '}
          <span className="text-white font-bold">▶ Run Scan</span>
          {' '}to evaluate all customer account health.
        </div>
      )}
    </div>
  )
}
