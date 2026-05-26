import { useState } from 'react'
import { runAgent } from '../services/api'

const STATUS = {
  CRITICAL: { border: 'border-danger',  badge: 'bg-danger/20  text-danger',  section: 'text-danger'  },
  NEGATIVE: { border: 'border-warning', badge: 'bg-warning/20 text-warning', section: 'text-warning' },
  HEALTHY:  { border: 'border-success', badge: 'bg-success/20 text-success', section: 'text-success' },
}

const PLATFORM_COLOR = {
  'Twitter/X':      'bg-sky-500/20     text-sky-300',
  Facebook:         'bg-blue-600/20    text-blue-300',
  Instagram:        'bg-pink-500/20    text-pink-300',
  LinkedIn:         'bg-blue-400/20    text-blue-200',
  YouTube:          'bg-red-500/20     text-red-300',
  'Google Reviews': 'bg-yellow-500/20  text-yellow-300',
  Trustpilot:       'bg-green-500/20   text-green-300',
  Reddit:           'bg-orange-500/20  text-orange-300',
  'App Store':      'bg-indigo-500/20  text-indigo-300',
  'Play Store':     'bg-teal-500/20    text-teal-300',
}

function platformColor(platform) {
  return PLATFORM_COLOR[platform] ?? 'bg-white/10 text-slate-300'
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

function ChannelCard({ report }) {
  const [open, setOpen] = useState(false)
  const st    = STATUS[report.status] ?? STATUS.HEALTHY
  const m     = report.metrics
  const alert = report.alert

  const npsVal       = parseFloat(m.nps_score)
  const negVal       = parseFloat(m.negative_sentiment)
  const complaintVal = parseFloat(m.complaint_volume)

  const npsLvl       = npsVal       < 20  ? (npsVal       < 0   ? 'critical' : 'warning') : 'normal'
  const negLvl       = negVal       > 30  ? (negVal       > 50  ? 'critical' : 'warning') : 'normal'
  const complaintLvl = complaintVal > 100 ? (complaintVal > 200 ? 'critical' : 'warning') : 'normal'

  return (
    <div className={`bg-panel border ${st.border} rounded-lg p-4 flex flex-col gap-3 transition-all`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-1 min-w-0">
          <span className="font-mono font-bold text-white text-sm truncate">{report.platform}</span>
          <div className="flex flex-wrap gap-1">
            <span className={`text-xs px-2 py-0.5 rounded font-mono ${platformColor(report.platform)}`}>
              {report.channel_id}
            </span>
            <span className="text-xs px-2 py-0.5 rounded font-mono bg-white/5 text-muted">
              {report.total_mentions?.toLocaleString()} mentions
            </span>
          </div>
        </div>
        <span className={`shrink-0 text-xs px-2 py-0.5 rounded-full font-mono ${st.badge}`}>
          {report.status}
        </span>
      </div>

      <div className="flex flex-wrap gap-1">
        <MetricPill label="NPS"        value={m.nps_score}          level={npsLvl}       />
        <MetricPill label="Neg Sent"   value={m.negative_sentiment} level={negLvl}       />
        <MetricPill label="Complaints" value={m.complaint_volume}   level={complaintLvl} />
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

function ChannelSection({ title, color, channels }) {
  if (!channels.length) return null
  return (
    <section>
      <h2 className={`text-xs font-mono uppercase tracking-widest mb-3 ${color}`}>
        {title} ({channels.length})
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {channels.map(r => <ChannelCard key={r.channel_id} report={r} />)}
      </div>
    </section>
  )
}

export default function SocialMediaAgent() {
  const [loading, setLoading] = useState(false)
  const [result,  setResult]  = useState(null)
  const [error,   setError]   = useState(null)

  const runScan = async () => {
    setLoading(true)
    setError(null)
    try {
      const resp = await runAgent('social-media', {
        query:      'Run full social media sentiment monitoring scan',
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
  const reports  = result?.channel_reports ?? []
  const critical = reports.filter(r => r.status === 'CRITICAL')
  const negative = reports.filter(r => r.status === 'NEGATIVE')
  const healthy  = reports.filter(r => r.status === 'HEALTHY')

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-bold text-white">Social Media Sentiment</h1>
          <p className="text-muted text-sm font-mono mt-1">
            10 channels &nbsp;·&nbsp; NPS / Negative Sentiment / Complaint Volume thresholds
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
          Fetching sentiment data → evaluating brand health thresholds → LLM root-cause analysis…
        </p>
      )}

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StatCard label="Total Channels" value={summary.total_channels} color="text-white"   />
          <StatCard label="Healthy"        value={summary.healthy}        color="text-success" />
          <StatCard label="Negative"       value={summary.negative}       color="text-warning" />
          <StatCard label="Critical"       value={summary.critical}       color="text-danger"  />
          <StatCard label="Alerts Raised"  value={summary.alerts_raised}  color="text-warning" />
        </div>
      )}

      {reports.length > 0 && (
        <div className="space-y-8">
          <ChannelSection title="Critical" color="text-danger"  channels={critical} />
          <ChannelSection title="Negative" color="text-warning" channels={negative} />
          <ChannelSection title="Healthy"  color="text-success" channels={healthy}  />
        </div>
      )}

      {!loading && !result && (
        <div className="text-center py-20 text-muted font-mono text-sm">
          Press <span className="text-white font-bold">▶ Run Scan</span> to monitor all social media channels.
        </div>
      )}
    </div>
  )
}
