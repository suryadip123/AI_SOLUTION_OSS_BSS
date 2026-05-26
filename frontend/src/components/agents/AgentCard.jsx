import { useNavigate } from 'react-router-dom'

const STATUS_STYLE = {
  active:  'bg-success/20 text-success',
  running: 'bg-warning/20 text-warning animate-pulse',
  idle:    'bg-slate-700 text-muted',
  error:   'bg-danger/20 text-danger',
}

export default function AgentCard({ id, label, sub, color, status }) {
  const navigate = useNavigate()
  return (
    <div
      onClick={() => navigate(`/${id}`)}
      className="bg-panel border border-slate-700 rounded-xl p-5 cursor-pointer
                 hover:border-primary hover:scale-[1.02] transition-all duration-200 group"
    >
      <div className="w-3 h-3 rounded-full mb-4" style={{ backgroundColor: color }} />
      <p className="font-display font-bold text-white text-base leading-tight">{label}</p>
      <p className="text-xs text-muted font-mono mt-1 mb-4">{sub}</p>
      <span className={`text-xs font-mono px-2 py-1 rounded-full ${STATUS_STYLE[status] ?? STATUS_STYLE.idle}`}>
        {status}
      </span>
    </div>
  )
}
