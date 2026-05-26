import { useState } from 'react'
import { runAgent } from '../services/api'

const STATUS = {
  CRITICAL: { border: 'border-danger',  badge: 'bg-danger/20  text-danger',  section: 'text-danger'  },
  AT_RISK:  { border: 'border-warning', badge: 'bg-warning/20 text-warning', section: 'text-warning' },
  HEALTHY:  { border: 'border-success', badge: 'bg-success/20 text-success', section: 'text-success' },
}

const SEGMENT_COLOR = {
  Enterprise: 'bg-blue-500/20   text-blue-300',
  SMB:        'bg-purple-500/20 text-purple-300',
  Retail:     'bg-cyan-500/20   text-cyan-300',
  Government: 'bg-orange-500/20 text-orange-300',
}

function segColor(seg) {
  return SEGMENT_COLOR[seg] ?? 'bg-white/10 text-slate-300'
}

function MetricPill({ label, value, level }) {
  const color = level === 'critical' ? 'bg-danger/20 text-danger' :
                level === 'warning'  ? 'bg-warning/20 text-warning' :
                                      'bg-white/5 text-muted'
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-mono ${color}`}>
      {label}: {value}
    </span>
  )
}

function BillingCard({ report }) {
  const [open, setOpen] = useState(false)
  const st    = STATUS[report.status] ?? STATUS.HEALTHY
  const m     = report.metrics
  const alert = report.alert

  const genVal     = parseFloat(m.bill_gen_rate)
  const payVal     = parseFloat(m.payment_rate)
  const disputeVal = parseFloat(m.dispute_rate)

  const genLvl     = genVal     < 85 ? (genVal     < 70 ? 'critical' : 'warning') : 'normal'
  const payLvl     = payVal     < 80 ? (payVal     < 60 ? 'critical' : 'warning') : 'normal'
  const disputeLvl = disputeVal > 10 ? (disputeVal > 20 ? 'critical' : 'warning') : 'normal'

  return (
    <div className={`bg-panel border ${st.border} rounded-lg p-4 flex flex-col gap-3 transition-all`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-1 min-w-0">
          <span className="font-mono font-bold text-white text-sm truncate">{report.name}</span>
          <div className="flex flex-wrap gap-1">
            <span className={`text-xs px-2 py-0.5 rounded font-mono ${segColor(report.segment)}`}>
              {report.segment}
            </span>
            <span className="text-xs px-2 py-0.5 rounded font-mono bg-white/5 text-muted">
              {report.region}
            </span>
            <span className="text-xs px-2 py-0.5 rounded font-mono bg-white/5 text-muted">
              {report.total_bills} bills
            </span>
          </div>
        </div>
        <span className={`shrink-0 text-xs px-2 py-0.5 rounded-full font-mono ${st.badge}`}>
          {report.status}
        </span>
      </div>

      <div className="flex flex-wrap gap-1">
        <MetricPill label="Bill Gen"  value={m.bill_gen_rate}  level={genLvl}     />
        <MetricPill label="Payment"   value={m.payment_rate}   level={payLvl}     />
        <MetricPill label="Disputes"  value={m.dispute_rate}   level={disputeLvl} />
      </div>

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

function BillingSection({ title, color, accounts }) {
  if (!accounts.length) return null
  return (
    <section>
      <h2 className={`text-xs font-mono uppercase tracking-widest mb-3 ${color}`}>
        {title} ({accounts.length})
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {accounts.map(r => <BillingCard key={r.account_id} report={r} />)}
      </div>
    </section>
  )
}

export default function BillingAgent() {
  const [loading, setLoading] = useState(false)
  const [result,  setResult]  = useState(null)
  const [error,   setError]   = useState(null)

  const runScan = async () => {
    setLoading(true)
    setError(null)
    try {
      const resp = await runAgent('billing', {
        query:      'Run full billing operations monitoring scan',
        session_id: `scan-${Date.now()}`,
      })
      setResult(resp.result)
    } catch (e) {
      setError(e?.response?.data?.detail ?? e.message ?? 'Scan failed')
    } finally {
      setLoading(false)
    }
  }

  const summary  = result?.summary
  const reports  = result?.billing_reports ?? []
  const critical = reports.filter(r => r.status === 'CRITICAL')
  const atRisk   = reports.filter(r => r.status === 'AT_RISK')
  const healthy  = reports.filter(r => r.status === 'HEALTHY')

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-bold text-white">Billing Operations</h1>
          <p className="text-muted text-sm font-mono mt-1">
            10 accounts &nbsp;·&nbsp; Bill Gen / Payment / Dispute Rate thresholds
          </p>
        </div>
        <button
          onClick={runScan}
          disabled={loading}
          className="shrink-0 px-5 py-2 bg-primary text-white rounded-lg font-mono text-sm
                     disabled:opacity-50 hover:bg-primary/80 transition-colors flex items-center gap-2"
        >
          {loading && (
            <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin inline-block" />
          )}
          {loading ? 'Scanning…' : '▶ Run Scan'}
        </button>
      </div>

      {error && (
        <div className="bg-danger/10 border border-danger rounded-lg p-4 text-danger font-mono text-sm">
          {error}
        </div>
      )}

      {loading && (
        <p className="text-muted font-mono text-sm animate-pulse">
          Fetching billing metrics → evaluating revenue thresholds → LLM root-cause analysis…
        </p>
      )}

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StatCard label="Total Accounts" value={summary.total_accounts} color="text-white"   />
          <StatCard label="Healthy"        value={summary.healthy}        color="text-success" />
          <StatCard label="At Risk"        value={summary.at_risk}        color="text-warning" />
          <StatCard label="Critical"       value={summary.critical}       color="text-danger"  />
          <StatCard label="Alerts Raised"  value={summary.alerts_raised}  color="text-warning" />
        </div>
      )}

      {reports.length > 0 && (
        <div className="space-y-8">
          <BillingSection title="Critical" color="text-danger"  accounts={critical} />
          <BillingSection title="At Risk"  color="text-warning" accounts={atRisk}   />
          <BillingSection title="Healthy"  color="text-success" accounts={healthy}  />
        </div>
      )}

      {!loading && !result && (
        <div className="text-center py-20 text-muted font-mono text-sm">
          Press <span className="text-white font-bold">▶ Run Scan</span> to monitor all billing accounts.
        </div>
      )}
    </div>
  )
}
