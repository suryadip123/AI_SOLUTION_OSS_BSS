import { useState } from 'react'
import { runAgent } from '../services/api'

// ── helpers ──────────────────────────────────────────────────────────────────

const STATUS = {
  CRITICAL: { border: 'border-danger',  badge: 'bg-danger/20  text-danger',  section: 'text-danger'  },
  DEGRADED: { border: 'border-warning', badge: 'bg-warning/20 text-warning', section: 'text-warning' },
  HEALTHY:  { border: 'border-success', badge: 'bg-success/20 text-success', section: 'text-success' },
}

const THRESHOLDS = {
  cpu:    { warn: 70, crit: 90 },
  loss:   { warn:  2, crit:  5 },
  latency:{ warn: 100, crit: 300 },
}

function breachLevel(value, key) {
  if (value > THRESHOLDS[key].crit) return 'critical'
  if (value > THRESHOLDS[key].warn) return 'warning'
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

function DeviceCard({ report }) {
  const [open, setOpen] = useState(false)
  const st    = STATUS[report.status] ?? STATUS.HEALTHY
  const m     = report.metrics
  const alert = report.alert

  const cpuLvl  = breachLevel(parseFloat(m.cpu),         'cpu')
  const lossLvl = breachLevel(parseFloat(m.packet_loss), 'loss')
  const latLvl  = breachLevel(parseFloat(m.latency),     'latency')

  return (
    <div className={`bg-panel border ${st.border} rounded-lg p-4 flex flex-col gap-3 transition-all`}>
      {/* title row */}
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono font-bold text-white text-sm truncate">{report.device}</span>
        <span className={`shrink-0 text-xs px-2 py-0.5 rounded-full font-mono ${st.badge}`}>
          {report.status}
        </span>
      </div>

      {/* metrics */}
      <div className="flex flex-wrap gap-1">
        <MetricPill label="CPU"  value={m.cpu}         level={cpuLvl}  />
        <MetricPill label="Loss" value={m.packet_loss} level={lossLvl} />
        <MetricPill label="Lat"  value={m.latency}     level={latLvl}  />
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

function DeviceSection({ title, color, devices }) {
  if (!devices.length) return null
  return (
    <section>
      <h2 className={`text-xs font-mono uppercase tracking-widest mb-3 ${color}`}>
        {title} ({devices.length})
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {devices.map(r => <DeviceCard key={r.device} report={r} />)}
      </div>
    </section>
  )
}

// ── page ─────────────────────────────────────────────────────────────────────

export default function NetworkAgent() {
  const [loading, setLoading] = useState(false)
  const [result,  setResult]  = useState(null)
  const [error,   setError]   = useState(null)

  const runScan = async () => {
    setLoading(true)
    setError(null)
    try {
      const resp = await runAgent('network', {
        query:      'Run full network outage monitoring scan',
        session_id: `scan-${Date.now()}`,
      })
      setResult(resp.result)
    } catch (e) {
      setError(e?.response?.data?.detail ?? e.message ?? 'Scan failed')
    } finally {
      setLoading(false)
    }
  }

  const summary   = result?.summary
  const reports   = result?.device_reports ?? []
  const critical  = reports.filter(r => r.status === 'CRITICAL')
  const degraded  = reports.filter(r => r.status === 'DEGRADED')
  const healthy   = reports.filter(r => r.status === 'HEALTHY')

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">

      {/* ── header ── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-bold text-white">
            Network Outage Monitor
          </h1>
          <p className="text-muted text-sm font-mono mt-1">
            10 devices &nbsp;·&nbsp; CPU / Packet Loss / Latency thresholds
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

      {/* ── error ── */}
      {error && (
        <div className="bg-danger/10 border border-danger rounded-lg p-4 text-danger font-mono text-sm">
          {error}
        </div>
      )}

      {/* ── scanning notice ── */}
      {loading && (
        <p className="text-muted font-mono text-sm animate-pulse">
          Fetching live metrics from DB → evaluating thresholds → LLM root-cause analysis…
        </p>
      )}

      {/* ── summary cards ── */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Total Devices" value={summary.total_devices} color="text-white"   />
          <StatCard label="Healthy"       value={summary.healthy}       color="text-success" />
          <StatCard label="Degraded"      value={summary.degraded}      color="text-warning" />
          <StatCard label="Critical"      value={summary.critical}      color="text-danger"  />
        </div>
      )}

      {/* ── device sections (critical first) ── */}
      {reports.length > 0 && (
        <div className="space-y-8">
          <DeviceSection title="Critical" color="text-danger"  devices={critical} />
          <DeviceSection title="Degraded" color="text-warning" devices={degraded} />
          <DeviceSection title="Healthy"  color="text-success" devices={healthy}  />
        </div>
      )}

      {/* ── empty state ── */}
      {!loading && !result && (
        <div className="text-center py-20 text-muted font-mono text-sm">
          Press{' '}
          <span className="text-white font-bold">▶ Run Scan</span>
          {' '}to monitor all network devices.
        </div>
      )}
    </div>
  )
}
