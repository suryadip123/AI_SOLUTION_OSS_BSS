# AI Solution OSS-BSS

> Multi-Agent Agentic AI Platform for Telecom OSS/BSS  
> **Stack**: FastAPI · LangGraph · React · SQLite · Ollama · Docker Compose

---

## Architecture

```
Data Domains (7)
      │
      ▼
Master Orchestrator Agent  ←── LangGraph StateGraph
      │
      ├── Network Agent            (Outage Prediction)
      ├── Customer Agent           (Order Health)
      ├── Service Fulfillment Agent
      ├── Service Assurance Agent  (Service Health)
      ├── Billing Agent            (Bill Automation)
      ├── Call Agent               (Call Analytics)
      └── Social Media Agent       (NPS / Sentiment)
            │
            ▼
   Telecom Service Optimization
```

---

## Quick Start

```bash
# 1. Copy env files
cp backend/.env.example backend/.env

# 2. Start all services
docker compose up --build

# 3. Pull Ollama model (first time)
docker exec oss_bss_ollama ollama pull llama3.2

# 4. Open
#   Frontend  → http://localhost:5173
#   API Docs  → http://localhost:8000/docs
#   Ollama    → http://localhost:11434
```

---

## Project Structure

```
AI_Solution_OSS_BSS/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config/settings.py  # Pydantic settings
│   │   ├── api/v1/             # REST endpoints (per domain)
│   │   ├── agents/             # LangGraph agents (per domain)
│   │   │   ├── base_agent.py   # Shared Ollama LLM factory
│   │   │   ├── orchestrator/   # Master Orchestrator
│   │   │   └── <domain>/       # state · nodes · tools · graph
│   │   ├── db/                 # SQLAlchemy + SQLite
│   │   ├── schemas/            # Pydantic request/response models
│   │   └── utils/              # Logger, helpers
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # React Router setup
│   │   ├── pages/              # One page per agent
│   │   ├── components/         # AgentCard, Sidebar, Navbar
│   │   ├── services/api.js     # Axios API client
│   │   └── store/agentStore.js # Zustand global state
│   ├── vite.config.js
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Implementation Steps

| Step | What |
|------|------|
| ✅ 0 | Project scaffold |
| ⬜ 1 | Database models + SQLite migration |
| ⬜ 2 | Network Agent — full LangGraph implementation |
| ⬜ 3 | Customer Agent |
| ⬜ 4 | Service Fulfillment Agent |
| ⬜ 5 | Service Assurance Agent |
| ⬜ 6 | Billing Agent |
| ⬜ 7 | Call Agent |
| ⬜ 8 | Social Media Agent |
| ⬜ 9 | Master Orchestrator — wires all agents |
| ⬜10 | React Dashboard — live agent UI |
| ⬜11 | Docker Compose — full integration test |
