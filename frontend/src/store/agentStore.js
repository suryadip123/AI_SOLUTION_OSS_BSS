import { create } from 'zustand'

const useAgentStore = create((set) => ({
  agents: {
    network:             { status: 'idle', result: null, loading: false },
    customer:            { status: 'idle', result: null, loading: false },
    service_fulfillment: { status: 'idle', result: null, loading: false },
    service_assurance:   { status: 'idle', result: null, loading: false },
    billing:             { status: 'idle', result: null, loading: false },
    call:                { status: 'idle', result: null, loading: false },
    social_media:        { status: 'idle', result: null, loading: false },
  },
  setAgentState: (name, patch) =>
    set(s => ({ agents: { ...s.agents, [name]: { ...s.agents[name], ...patch } } })),
}))

export default useAgentStore
