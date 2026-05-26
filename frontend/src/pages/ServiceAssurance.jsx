import { useState } from 'react'
import { runAgent } from '../services/api'

const STATUS = {
  CRITICAL: { border: 'border-danger',  badge: 'bg-danger/20  text-danger',  section: 'text-danger'  },
  DEGRADED: { border: 'border-warning', badge: 'bg-warning/20 text-warning', section: 'text-warning' },
  HEALTHY:  { border: 'border-success', badge: 'bg-success/20 text-success', section: 'text-success' },
}

const TYPE_COLOR = {
  VoIP:     'bg-blue-500/20   text-blue-300',
  Internet: 'bg-cyan-500/20   text-cyan-300',
  Mobile:   'bg-purple-500/20 text-purple-300',
  '5G':     'bg-pink-500/20   text-pink-300',
  IPTV:     'bg-orange-500/20 text-orange-300',
  VPN:      'bg-teal-500/20   text-teal-300',
}

function typeColor(serviceType) {
  for (const k of Object.keys(TYPE_COLOR)) {
    if (serviceType.startsWith(k)) return TYPE_COLOR[k]
  }
  return 'bg-white/10 text-slate-300'
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

function ServiceCard({ report }) {
  const [open, setOpen] = useState(false)
  const st    = STATUS[report.status] ?? STATUS.HEALTHY
  const m     = report.metrics
  const alert = report.alert

  const availVal = parseFloat(m.availability)
  const errVal   = parseFloat(m.error_rate)
  const mttrVal  = parseFloat(m.mttr)

  const availLvl = availVal < 95 ? (availVal < 90 ? 'critical' : 'warning') : 'normal'
  const errLvl   = errVal   > 5  ? (errVal   > 10 ? 'critical' : 'warning') : 'normal'
  const mttrLvl  = mttrVal  > 4  ? (mttrVal  > 8  ? 'critical' : 'warning') : 'normal'

  return (
    <div className={`bg-panel border ${st.border} rounded-lg p-4 flex flex-col gap-3 transition-all`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-1 min-w-0">
          <span className="font-mono font-bold text-white text-sm truncate">{report.name}</span>
          <div className="flex flex-wrap gap-1">
            <span className={`text-xs px-2 py-0.5 rounded font-mono ${typeColor(report.service_type)}`}>
              {report.service_type}
            </span>
            <span className="text-xs px-2 py-0.5 rounded font-mono bg-white/5 text-muted">
              {report.region}
            </span>
          </div>
        </div>
        <span className={`shrink-0 text-xs px-2 py-0.5 rounded-full font-mono ${st.badge}`}>
          {report.status}
        </span>
      </div>

      <div className="flex flex-wrap gap-1">
        <MetricPill label="Avail"    value={m.availability} level={availLvl} />
        <MetricPill label="Err Rate" value={m.error_rate}   level={errLvl}   />
        <MetricPill label="MTTR"     value={m.mttr}         level={mttrLvl}  />
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

function ServiceSection({ title, color, services }) {
  if (!services.length) return null
  return (
    <section>
      <h2 className={`text-xs font-mono uppercase tracking-widest mb-3 ${color}`}>
        {title} ({services.length})
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {services.map(r => <ServiceCard key={r.service_id} report={r} />)}
      </div>
    </section>
  )
}

export default function ServiceAssurance() {
  const [loading, setLoading] = useState(false)
  const [result,  setResult]  = useState(null)
  const [error,   setError]   = useState(null)

  const runScan = async () => {
    setLoading(true)
    setError(null)
    try {
      const resp = await runAgent('service-assurance', {
        query:      'Run full service assurance monitoring scan',
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
  const reports  = result?.service_reports ?? []
  const critical = reports.filter(r => r.status === 'CRITICAL')
  const degraded = reports.filter(r => r.status === 'DEGRADED')
  const healthy  = reports.filter(r => r.status === 'HEALTHY')

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-bold text-white">Service Assurance</h1>
          <p className="text-muted text-sm font-mono mt-1">
            10 services &nbsp;·&nbsp; Availability / Error Rate / MTTR thresholds
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
          Fetching service metrics → evaluating SLA thresholds → LLM root-cause analysis…
        </p>
      )}

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StatCard label="Total Services" value={summary.total_services}  color="text-white"   />
          <StatCard label="Healthy"        value={summary.healthy}         color="text-success" />
          <StatCard label="Degraded"       value={summary.degraded}        color="text-warning" />
          <StatCard label="Critical"       value={summary.critical}        color="text-danger"  />
          <StatCard label="Alerts Raised"  value={summary.alerts_raised}   color="text-warning" />
        </div>
      )}

      {reports.length > 0 && (
        <div className="space-y-8">
          <ServiceSection title="Critical" color="text-danger"  services={critical} />
          <ServiceSection title="Degraded" color="text-warning" services={degraded} />
          <ServiceSection title="Healthy"  color="text-success" services={healthy}  />
        </div>
      )}

      {!loading && !result && (
        <div className="text-center py-20 text-muted font-mono text-sm">
          Press <span className="text-white font-bold">▶ Run Scan</span> to monitor all services.
        </div>
      )}
    </div>
  )
}
