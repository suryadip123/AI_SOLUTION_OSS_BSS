import AgentCard from '../components/agents/AgentCard'

const AGENTS = [
  { id: 'network',             label: 'Network Agent',             color: '#22C55E', status: 'active',  sub: 'Outage Prediction'     },
  { id: 'customer',            label: 'Customer Agent',            color: '#7B2D8B', status: 'idle',    sub: 'Order Health'          },
  { id: 'service-fulfillment', label: 'Service Fulfillment Agent', color: '#1A7A4A', status: 'idle',    sub: 'Order Processing'      },
  { id: 'service-assurance',   label: 'Service Assurance Agent',   color: '#E8720C', status: 'running', sub: 'Service Health'        },
  { id: 'billing',             label: 'Billing Agent',             color: '#A0195A', status: 'idle',    sub: 'Bill Automation'       },
  { id: 'call',                label: 'Call Agent',                color: '#2E3A45', status: 'idle',    sub: 'Call Analytics'        },
  { id: 'social-media',        label: 'Social Media Agent',        color: '#1A5C2A', status: 'idle',    sub: 'NPS / Sentiment'       },
]

export default function Dashboard() {
  return (
    <div>
      <h1 className="text-3xl font-display font-bold text-white mb-1">Agentic AI — OSS/BSS</h1>
      <p className="text-muted text-sm mb-8 font-mono">Multi-Agent Architecture · Telecom Service Optimization</p>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {AGENTS.map(a => <AgentCard key={a.id} {...a} />)}
      </div>
    </div>
  )
}
