import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1', timeout: 180000 })

export const runAgent = (domain, payload) =>
  api.post(`/${domain}/run`, payload).then(r => r.data)

export const getAgentStatus = (domain) =>
  api.get(`/${domain}/status`).then(r => r.data)

export default api
