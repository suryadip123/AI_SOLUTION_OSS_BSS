import { NavLink } from 'react-router-dom'

const NAV = [
  { to: '/',                    label: '⬡  Dashboard'           },
  { to: '/network',             label: '📡 Network'             },
  { to: '/customer',            label: '👤 Customer'            },
  { to: '/service-fulfillment', label: '⚙️  Service Fulfillment' },
  { to: '/service-assurance',   label: '🛡  Service Assurance'   },
  { to: '/billing',             label: '💳 Billing'             },
  { to: '/call',                label: '📞 Call'                },
  { to: '/social-media',        label: '💬 Social Media'        },
]

export default function Sidebar() {
  return (
    <aside className="w-56 bg-panel border-r border-slate-700 flex flex-col py-6 gap-1">
      <div className="px-5 mb-6">
        <p className="font-display font-bold text-white text-lg leading-tight">OSS/BSS</p>
        <p className="text-xs text-muted font-mono">Agentic AI Platform</p>
      </div>
      {NAV.map(n => (
        <NavLink key={n.to} to={n.to} end={n.to==='/'} className={({isActive}) =>
          `px-5 py-2 text-sm font-mono transition-all ${isActive ? 'bg-primary/20 text-white border-l-2 border-primary' : 'text-muted hover:text-white hover:bg-white/5'}`}>
          {n.label}
        </NavLink>
      ))}
    </aside>
  )
}
