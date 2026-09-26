# Small Language Model (SLM) for Intelligent Service Level Management in IT Infrastructure Services

[![Status: Work in Progress](https://img.shields.io/badge/status-Work%20in%20Progress-amber.svg)](https://github.com/fawaz165/intelligent-service-level-management-slm)
[![Repo](https://img.shields.io/badge/repo-islm--small--language--model-blue.svg)](https://github.com/fawaz165/intelligent-service-level-management-slm)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57.svg)](https://www.sqlite.org/)
[![Ollama](https://img.shields.io/badge/Ollama-DeepSeek--R1%3A1.5B-black.svg)](https://ollama.com/)

> **Project / Repo:** `islm-small-language-model`  
> **Status:** ⚠️ **Work in Progress (Active Development)**

---

## 📌 Overview

**ISLM** is a privacy-first conversational IT Service Management system powered by an on-premise Small Language Model (**DeepSeek-R1:1.5B via Ollama**). It allows IT engineers and administrators to manage service tickets, monitor infrastructure SLAs, and upload incident files using natural language.

### 🔒 Zero-Trust SLM Security
The language model **never generates or executes raw SQL directly**. Instead:
```
User Prompt ──> SLM (Ollama) ──> Structured JSON Intent ──> Pydantic Validation ──> SQLAlchemy ORM ──> SQLite DB
```

---

## 🎯 Key Objectives & Features

- **Natural Language CRUD**: Query, create, update, and resolve infrastructure tickets with plain English.
- **100% Local Inference**: Zero data leakage or cloud API costs using an edge-friendly 1.5B SLM.
- **Safe Destructive Actions**: Confirmation modals guard deletion of tickets and services.
- **Dynamic Tables**: Query results render as interactive, styled data tables with status badges.
- **File Management**: Upload logs, crash dumps, and diagnostic files with whitelist and size controls.
- **Real-Time Health Monitoring**: Status bar tracks live connectivity of both database and Ollama.

---

## 🏗️ Architecture & Tech Stack

```
React 18 + Vite (Port 5173) ──[HTTP REST]──> FastAPI Backend (Port 8000)
                                                ├── Ollama (DeepSeek-R1:1.5B, Port 11434)
                                                ├── SQLite (islm.db via SQLAlchemy)
                                                └── Local Storage (`storage/`)
```

| Layer | Technology |
|---|---|
| **Frontend** | React 18, Vite 5, Vanilla CSS |
| **Backend** | Python 3.10+, FastAPI, Uvicorn, Pydantic |
| **Database** | SQLite 3 with WAL mode, SQLAlchemy ORM |
| **SLM Engine** | Ollama with `deepseek-r1:1.5b` |

---

## 📂 Project Structure

```text
islm-small-language-model/
├── backend/               # FastAPI backend
│   ├── api/               # REST routes (chat, tickets, services, files, health)
│   ├── database/          # SQLAlchemy models, schemas, seed data
│   ├── services/          # Business logic & Ollama LLM service
│   ├── tools/             # Intent dispatcher
│   ├── prompts/           # SLM prompt definitions
│   └── requirements.txt   # Python dependencies
├── frontend/              # React frontend (Vite)
│   ├── src/components/    # UI components (ChatInput, DataTable, StatusBar, etc.)
│   └── src/App.jsx        # Main application
├── database/schema.sql    # Relational reference schema
├── storage/               # Uploaded incident attachments
├── .env.example           # Environment template
├── start.bat              # One-click startup script (Windows)
└── README.md
```

---

## 🗄️ Database Schema

The database models ITIL-aligned service desk workflows:
- `users`: IT support personnel and managers.
- `services`: Monitored infrastructure services (Databases, API Gateways, Networks).
- `tickets`: Incident records with priority, status, category, and foreign keys.
- `sla`: Response and resolution time targets per service and priority tier.
- `files`: Metadata and file system paths for incident attachments.

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+** | **Node.js 18+** | **Ollama** ([ollama.com](https://ollama.com/))

### 2. Pull the SLM Model
```bash
ollama pull deepseek-r1:1.5b
```

### 3. Automated One-Click Launch (Windows)
Simply run:
```bat
start.bat
```
*(Automatically checks tools, installs dependencies, seeds the database, and launches both servers).*

---

### Manual Launch

**Backend Setup:**
```bash
# Setup environment
copy .env.example .env    # Linux/Mac: cp .env.example .env

# Install dependencies & seed
pip install -r backend/requirements.txt
python -m backend.database.seed

# Start backend
uvicorn backend.main:app --reload --port 8000
```
*API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)*

**Frontend Setup:**
```bash
cd frontend
npm install
npm run dev
```
*App URL: [http://localhost:5173](http://localhost:5173)*

---

## 💡 Example Prompts

| Intent | Example Prompt |
|---|---|
| **Query** | *"Show all open network tickets"* |
| **Filter** | *"List high-priority tickets assigned to Bob"* |
| **Create** | *"Create a critical database ticket titled 'Connection pool exhausted'"* |
| **Update** | *"Change ticket 3 status to resolved"* |
| **Delete** | *"Delete ticket 7"* *(Triggers confirmation modal)* |
| **Files** | Click 📎 to upload logs, or ask *"Show all uploaded log files"* |

---

## 🔮 Future Roadmap

- [ ] Predictive SLA breach alerts based on resolution velocity.
- [ ] Multi-agent automated triage and root-cause analysis.
- [ ] Enterprise SSO / RBAC authentication.
- [ ] Native Prometheus / Grafana alert webhooks.
- [ ] RAG with local vector storage for IT runbooks.

---

## 📄 License

MIT License.
