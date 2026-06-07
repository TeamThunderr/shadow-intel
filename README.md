# Shadow Intel

> **Multi-Agent Financial Crime Intelligence Platform**
> Microsoft Agents League Hackathon 2026

---

## Overview

Shadow Intel is a five-agent AI platform that investigates financial crime by simultaneously querying sanctions databases, tracing blockchain flows, unwinding corporate shells, and monitoring dark-web OSINT signals.

| Agent | Role | Data Sources |
|-------|------|-------------|
| **Ghost Tracker** | Sanctions matching + entity fingerprinting | OFAC, OpenSanctions, UN, OpenCorporates |
| **Money Trail** | Blockchain tracing + FinCEN cross-reference | Etherscan, FinCEN |
| **Ownership Unwind** | Recursive UBO graph, shell detection | OpenOwnership, Companies House, SEC EDGAR |
| **Dark Signal** | OSINT: leaked docs, news, OCCRP | ICIJ, OCCRP Aleph, GDELT |
| **Resurface Engine** | Watchlist monitor + Teams/Outlook alerts | OpenCorporates, WHOIS, Graph API |

All agents feed into the **Foundry IQ** orchestrator (Azure AI Foundry / GPT-4o) which generates a detective-style narrative report.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 + FastAPI + async agents |
| AI Orchestration | Azure AI Foundry (GPT-4o) |
| Data Lakehouse | Microsoft Fabric |
| Alerts | Microsoft Graph API (Teams + Outlook) |
| Frontend | React 18 + Vite + D3.js |
| Infra | Docker Compose |

---

## Quick Start (Local Dev)

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp ../.env.example .env         # fill in API keys
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

UI: http://localhost:5173

### Docker (full stack)

```bash
cp .env.example backend/.env    # fill in your keys
docker compose up --build
```

---

## Environment Variables

Copy `.env.example` → `backend/.env` and fill in:

- **Azure Foundry**: `AZURE_FOUNDRY_ENDPOINT`, `AZURE_FOUNDRY_API_KEY`
- **Fabric**: `FABRIC_WORKSPACE_ID`, `FABRIC_LAKEHOUSE_ID`, `FABRIC_CLIENT_*`
- **Graph API**: `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET`, `GRAPH_TENANT_ID`, `GRAPH_TEAMS_*`
- **OpenSanctions**: `OPENSANCTIONS_API_KEY`
- **OpenCorporates**: `OPENCORPORATES_API_KEY`
- **Companies House**: `COMPANIES_HOUSE_API_KEY`
- **OCCRP Aleph**: `OCCRP_API_KEY`
- **Etherscan**: `ETHERSCAN_API_KEY`

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/investigate` | Start investigation |
| `GET` | `/investigate/{id}/status` | Poll agent statuses |
| `GET` | `/investigate/{id}` | Get full report |
| `GET` | `/watchlist` | List watchlist |
| `POST` | `/watchlist` | Add entity |
| `DELETE` | `/watchlist/{id}` | Remove entity |
| `GET` | `/report/{id}/markdown` | Download markdown report |
| `GET` | `/report/{id}/pdf` | Download PDF report |
| `GET` | `/health` | Health check |

---

## Project Structure

```
backend/
  agents/           # Five specialised AI agents
  orchestrator/     # Evidence merger + Foundry IQ narrative
  fabric/           # Microsoft Fabric data pipelines
  alerts/           # Teams + Outlook notifications
  api/              # FastAPI routes
  shared/           # Config, schemas, utilities
frontend/
  src/
    pages/          # Home, Investigation, Watchlist, AlertHistory
    components/     # D3 graphs, status panels, search
    api/            # Axios client
```

---

## Implementation Status

| Module | Status |
|--------|--------|
| Backend skeleton | ✅ Complete |
| Schemas + base agent | ✅ Complete |
| GhostTracker agent | 🔶 Stub (sources need API key) |
| MoneyTrail agent | 🔶 Stub (P2) |
| OwnershipUnwind agent | 🔶 Stub (P3) |
| DarkSignal agent | 🔶 Stub — GDELT implemented (P3) |
| Resurface engine | 🔶 Stub (P4) |
| Foundry IQ orchestrator | ✅ Complete (needs API key) |
| Fabric pipelines | 🔶 Stub (needs Fabric workspace) |
| Teams/Outlook alerts | ✅ Complete (needs Graph creds) |
| Frontend UI | ✅ Complete |
| Docker Compose | ✅ Complete |

---

*Built for Microsoft Agents League Hackathon 2026*