import { useState } from 'react'
import { runAgent } from '../services/api'

// ── constants ─────────────────────────────────────────────────────────────────

const SLA_STYLE = {
  BREACHED: { border: 'border-danger',  badge: 'bg-danger/20  text-danger',  label: 'text-danger'  },
  AT_RISK:  { border: 'border-warning', badge: 'bg-warning/20 text-warning', label: 'text-warning' },
  ON_TRACK: { border: 'border-success', badge: 'bg-success/20 text-success', label: 'text-success' },
}

const STATUS_COLOR = {
  FAILED:       'text-danger',
  TESTING:      'text-primary',
  PROVISIONING: 'text-warning',
  VALIDATING:   'text-muted',
  PENDING:      'text-muted',
}

const STEP_STATUS_COLOR = {
  COMPLETED: 'text-success',
  RUNNING:   'text-warning',
  FAILED:    'text-danger',
  PENDING:   'text-slate-600',
}

const TYPE_LABELS = {
  SIM_ACTIVATION:  'SIM Activation',
  BROADBAND:       'Broadband',
  NUMBER_PORTING:  'Number Porting',
}

const SEV_COLOR = {
  CRITICAL: 'text-danger',
  HIGH:     'text-orange-400',
  MEDIUM:   'text-warning',
  LOW:      'text-muted',
}

// ── sub-components ────────────────────────────────────────────────────────────

function SlaBar({ pct }) {
  const clamped = Math.min(parseFloat(pct), 120)
  const fill    = clamped > 100 ? 'bg-danger' : clamped >= 80 ? 'bg-warning' : 'bg-success'
  return (
    <div className="w-full bg-slate-700 rounded-full h-1.5 mt-1">
      <div className={`${fill} h-1.5 rounded-full transition-all`} style={{ width: `${Math.min(clamped, 100)}%` }} />
    </div>
  )
}

function StepPill({ step }) {
  const color = STEP_STATUS_COLOR[step.status] ?? 'text-muted'
  return (
    <span className={`text-xs font-mono px-1.5 py-0.5 rounded bg-white/5 ${color}`}>
      {step.step}{step.duration ? ` (${step.duration})` : ''}
      {step.status === 'FAILED' ? ' ✕' : step.status === 'COMPLETED' ? ' ✓' : step.status === 'RUNNING' ? ' ↻' : ''}
    </span>
  )
}

function RcaBlock({ rca }) {
  if (!rca || !rca.what) return null
  return (
    <div className="space-y-1.5 mt-2 border-t border-slate-700 pt-2">
      {[
        ['WHAT',       rca.what,       'text-white'],
        ['WHY',        rca.why,        'text-white'],
        ['IMPACT',     rca.impact,     'text-warning'],
        ['FIX',        rca.fix,        'text-success'],
        ['PREVENTION', rca.prevention, 'text-primary'],
      ].map(([label, val, color]) => val && (
        <div key={label}>
          <span className="text-muted">{label}: </span>
          <span className={`${color} leading-relaxed`}>{val}</span>
        </div>
      ))}
    </div>
  )
}

function OrderCard({ report }) {
  const [open, setOpen] = useState(false)
  const st     = SLA_STYLE[report.sla_status] ?? SLA_STYLE.ON_TRACK
  const m      = report.metrics
  const alert  = report.alert
  const pct    = parseFloat(m.elapsed_pct)

  return (
    <div className={`bg-panel border ${st.border} rounded-lg p-4 flex flex-col gap-3`}>
      {/* header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-mono font-bold text-white text-sm">{report.order_id}</p>
          <p className="text-xs text-muted font-mono truncate">{report.customer_name}</p>
        </div>
        <span className={`shrink-0 text-xs px-2 py-0.5 rounded-full font-mono ${st.badge}`}>
          {report.sla_status}
        </span>
      </div>

      {/* type + status */}
      <div className="flex flex-wrap gap-1">
        <span className="text-xs px-2 py-0.5 rounded font-mono bg-primary/20 text-primary">
          {TYPE_LABELS[report.order_type] ?? report.order_type}
        </span>
        <span className={`text-xs px-2 py-0.5 rounded font-mono bg-white/5 ${STATUS_COLOR[report.status] ?? 'text-muted'}`}>
          {report.status}
        </span>
        {alert.is_ambiguous && (
          <span className="text-xs px-2 py-0.5 rounded font-mono bg-orange-500/20 text-orange-300">
            ⚠ AMBIGUOUS
          </span>
        )}
      </div>

      {/* SLA progress */}
      <div>
        <div className="flex justify-between text-xs font-mono text-muted">
          <span>SLA: {m.elapsed_hours} / {m.sla_hours}</span>
          <span className={st.label}>{m.elapsed_pct}</span>
        </div>
        <SlaBar pct={pct} />
      </div>

      {/* step timeline */}
      <div className="flex flex-wrap gap-1">
        {(report.steps ?? []).map(s => <StepPill key={s.step} step={s} />)}
      </div>

      {/* alert expand */}
      {alert.raised && (
        <div>
          <button
            onClick={() => setOpen(o => !o)}
            className="text-xs font-mono text-muted hover:text-white underline"
          >
            {open ? 'Hide RCA ▲' : `Show RCA ▼ (${alert.severity})`}
          </button>
          {open && (
            <div className="mt-3 text-xs font-mono space-y-2">
              {/* individual alerts */}
              {(alert.alerts ?? []).map((a, i) => (
                <p key={i} className={`${SEV_COLOR[a.severity] ?? 'text-muted'}`}>
                  [{a.type}] {a.reason}
                </p>
              ))}

              {/* LLM RCA */}
              <RcaBlock rca={alert.rca} />

              {alert.recommendation && (
                <div className="border-t border-slate-700 pt-2">
                  <p className="text-muted mb-0.5">Recommendation</p>
                  <p className="text-success leading-relaxed">{alert.recommendation}</p>
                </div>
              )}
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

function Section({ title, color, orders }) {
  if (!orders.length) return null
  return (
    <section>
      <h2 className={`text-xs font-mono uppercase tracking-widest mb-3 ${color}`}>
        {title} ({orders.length})
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {orders.map(r => <OrderCard key={r.order_id} report={r} />)}
      </div>
    </section>
  )
}

// ── page ──────────────────────────────────────────────────────────────────────

export default function ServiceFulfillment() {
  const [loading, setLoading] = useState(false)
  const [result,  setResult]  = useState(null)
  const [error,   setError]   = useState(null)

  const runScan = async () => {
    setLoading(true)
    setError(null)
    try {
      const resp = await runAgent('service-fulfillment', {
        query:      'Run full service fulfillment order health scan',
        session_id: `sf-scan-${Date.now()}`,
      })
      setResult(resp.result)
    } catch (e) {
      setError(e?.response?.data?.detail ?? e.message ?? 'Scan failed')
    } finally {
      setLoading(false)
    }
  }

  const summary  = result?.summary
  const reports  = result?.order_reports ?? []
  const breached = reports.filter(r => r.sla_status === 'BREACHED')
  const atRisk   = reports.filter(r => r.sla_status === 'AT_RISK')
  const onTrack  = reports.filter(r => r.sla_status === 'ON_TRACK')

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">

      {/* header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-bold text-white">Service Fulfillment</h1>
          <p className="text-muted text-sm font-mono mt-1">
            Active orders &nbsp;·&nbsp; SLA tracking · Step lifecycle · RCA
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
          Fetching active orders → evaluating SLA + step health → LLM RCA analysis…
        </p>
      )}

      {/* summary */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StatCard label="Total Orders"  value={summary.total_orders}  color="text-white"   />
          <StatCard label="On Track"      value={summary.on_track}      color="text-success" />
          <StatCard label="At Risk"       value={summary.at_risk}       color="text-warning" />
          <StatCard label="Breached"      value={summary.breached}      color="text-danger"  />
          <StatCard label="Failed"        value={summary.failed}        color="text-danger"  />
        </div>
      )}

      {/* order sections */}
      {reports.length > 0 && (
        <div className="space-y-8">
          <Section title="SLA Breached" color="text-danger"  orders={breached} />
          <Section title="At Risk"      color="text-warning" orders={atRisk}   />
          <Section title="On Track"     color="text-success" orders={onTrack}  />
        </div>
      )}

      {/* empty state */}
      {!loading && !result && (
        <div className="text-center py-20 text-muted font-mono text-sm">
          Press{' '}
          <span className="text-white font-bold">▶ Run Scan</span>
          {' '}to monitor all active service orders.
        </div>
      )}
    </div>
  )
}
