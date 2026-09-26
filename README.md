# Small Language Model (SLM) for Intelligent Service Level Management in IT Infrastructure Services

[![Project Status: Work in Progress](https://img.shields.io/badge/status-Work%20in%20Progress-amber.svg)](https://github.com/fawaz165/intelligent-service-level-management-slm)
[![Repository](https://img.shields.io/badge/repo-islm--small--language--model-blue.svg)](https://github.com/fawaz165/intelligent-service-level-management-slm)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF.svg)](https://vitejs.dev/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57.svg)](https://www.sqlite.org/)
[![Ollama](https://img.shields.io/badge/Ollama-DeepSeek--R1%3A1.5B-black.svg)](https://ollama.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Repository Name:** `islm-small-language-model`  
> **Status:** ⚠️ **Work in Progress (Active Research & Development)**

---

## 📌 Project Overview

**Intelligent Service Level Management (ISLM)** is an enterprise IT infrastructure management platform driven by a locally deployed **Small Language Model (SLM)**. Traditional IT Service Management (ITSM) workflows require navigating complex ticketing forms, running rigid database queries, or mastering dashboard query languages. 

ISLM replaces manual operational friction with an intuitive conversational interface powered by **DeepSeek-R1:1.5B** running locally through **Ollama**. IT administrators, support engineers, and operations personnel can manage service tickets, monitor infrastructure health, inspect SLA compliance, and attach technical incident documentation using natural language in plain English.

Crucially, ISLM is engineered with privacy and deterministic safety: **the language model never generates or executes raw SQL**. Instead, the SLM interprets natural language requests into structured JSON intents, which are strictly validated by backend Pydantic schemas and executed through SQLAlchemy parameterized queries.

---

## 🎯 Objectives

1. **Natural Language ITSM Automation**: Enable IT staff and system administrators to query, create, update, and resolve infrastructure tickets using conversational dialogue.
2. **Edge & Local Privacy**: Ensure 100% data confidentiality and zero API dependency by hosting the Small Language Model on-premise/locally via Ollama without leaking sensitive infrastructure telemetry to third-party clouds.
3. **Deterministic & Secure Execution**: Bridge the gap between stochastic language models and relational DBMS integrity through deterministic schema validation and parameterized ORM transactions.
4. **Comprehensive Infrastructure Visibility**: Integrate services, SLA thresholds, incident histories, team assignments, and troubleshooting files into a unified relational schema.
5. **Lightweight Footprint**: Utilize an efficient 1.5B parameter SLM (DeepSeek-R1:1.5B) capable of running on standard commodity hardware, developer workstations, and edge servers.

---

## ✨ Key Features

- 💬 **Conversational CRUD Operations**: Perform full Create, Read, Update, and Delete actions on infrastructure incidents and services using conversational language.
- 🛡️ **Guarded Destructive Actions**: Destructive operations (such as deleting tickets or services) trigger interactive confirmation dialogs with clear impact summaries before execution.
- 📊 **Dynamic Tabular Visualizations**: Query results automatically render as interactive, formatted data tables with status badges, priority markers, and timestamps.
- 📎 **Secure File & Log Management**: Upload incident crash dumps, log traces, screenshots, and network diagnostics with file type whitelisting and size restrictions.
- 🚦 **Real-Time System Health Monitoring**: A persistent status bar tracks the live connectivity and operational readiness of the Ollama SLM engine and SQLite database.
- ⚡ **One-Click Local Launcher**: Includes a automated `start.bat` script that checks prerequisites, pulls the SLM model if missing, installs dependencies, seeds the database, and boots both servers concurrently.

---

## 🏗️ System Architecture

ISLM follows a modern, decoupled client-server architecture with an isolated local inference layer.

```
┌─────────────────────────────────────────────────────────────┐
│                       Client Layer                          │
│     React 18 + Vite Chat Interface (http://localhost:5173)   │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / REST JSON
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend Core                     │
│                 (http://localhost:8000)                     │
│                                                             │
│   ┌──────────────┐     ┌──────────────┐     ┌───────────┐  │
│   │  API Router  │ ──> │ Intent Engine│ ──> │ Pydantic  │  │
│   │ (REST /chat) │     │ (Dispatcher) │     │ Validator │  │
│   └──────────────┘     └──────────────┘     └───────────┘  │
│           │                   │                            │
└───────────┼───────────────────┼─────────────────────────────┘
            │                   │
    HTTP    ▼                   ▼ SQLAlchemy ORM
┌───────────────────────┐   ┌────────────────────────────────┐
│   Ollama SLM Host     │   │      SQLite Database Layer     │
│ (http://localhost:11434)  │   │          (islm.db)             │
│                       │   │  - Users, Services, Tickets    │
│   DeepSeek-R1:1.5B    │   │  - SLA Targets, File Metadata  │
└───────────────────────┘   └────────────────────────────────┘
                                    │
                                    ▼ Local Storage
                            ┌────────────────────────────────┐
                            │    File System (`storage/`)    │
                            │  Logs, Dumps, Incident Files   │
                            └────────────────────────────────┘
```

### 🔒 Security & Safe Execution Pipeline

Unlike naive LLM-to-SQL systems that expose databases to prompt injection and hallucinated SQL queries, ISLM enforces a zero-trust model:

```
User Prompt ──> SLM Prompt Template ──> Ollama Inference
                                                │
                                                ▼ (Structured JSON Intent Only)
                                       JSON Validation & Sanitization
                                                │
                                                ▼
                                    Backend Dispatcher & ORM
                                                │
                                                ▼ (Parameterized Query)
                                        SQLite Database
```

---

## 💻 Technologies Used

### Frontend
- **Framework**: [React 18](https://react.dev/)
- **Build Tool**: [Vite 5](https://vitejs.dev/)
- **Styling**: Vanilla CSS (Custom design system with dark mode glassmorphism, responsive tables, and status badges)
- **Networking**: Native Fetch API with Vite reverse-proxy configuration

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous ASGI Web Framework)
- **Server**: [Uvicorn](https://www.uvicorn.org/) (High-performance ASGI HTTP server)
- **Data Validation**: [Pydantic](https://docs.pydantic.dev/)
- **Configuration**: `python-dotenv` with strongly typed settings

### Database & Storage
- **Database Engine**: [SQLite 3](https://www.sqlite.org/) with Write-Ahead Logging (WAL)
- **ORM & Migrations**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
- **Local Storage**: Filesystem storage for uploaded incident attachments with UUID and name sanitization

### Small Language Model (SLM) & AI
- **Runtime**: [Ollama](https://ollama.com/) (Local model management and inference engine)
- **Model**: `deepseek-r1:1.5b` (Optimized reasoning small language model)
- **Prompt Engineering**: Custom system prompts enforcing JSON-only structured output and intent classification

---

## 📂 Project Structure

```text
islm-small-language-model/
├── .env.example               # Environment variables configuration template
├── .gitignore                  # Git ignore rules for Python, Node, SQLite & IDEs
├── README.md                   # Comprehensive project documentation
├── start.bat                   # Windows batch script for automated startup
├── islm.db                     # SQLite database (generated upon seeding, gitignored)
│
├── backend/                    # FastAPI backend service
│   ├── main.py                 # FastAPI application entry point & CORS configuration
│   ├── config.py               # Environment and application configuration loader
│   ├── requirements.txt        # Python dependency manifest
│   │
│   ├── api/                    # REST API route controllers
│   │   ├── chat.py             # Chat endpoint with SLM integration
│   │   ├── tickets.py          # Ticket CRUD operations
│   │   ├── services.py         # Service catalog endpoints
│   │   ├── files.py            # File upload and download handlers
│   │   └── health.py           # System health, DB, and Ollama probe
│   │
│   ├── database/               # Database management and models
│   │   ├── connection.py       # SQLAlchemy engine and session factory
│   │   ├── models.py           # Relational SQLAlchemy database models
│   │   ├── schemas.py          # Pydantic schemas for request/response serialization
│   │   ├── seed.py             # Database seed script for mock infrastructure data
│   │   ├── reseed.py           # Database purge and reset utility
│   │   ├── test_llm.py         # LLM connectivity and prompt test harness
│   │   └── DATASETS.md         # Reference synthetic dataset documentation
│   │
│   ├── services/               # Core business logic layer
│   │   ├── llm_service.py      # Ollama HTTP client and prompt generation
│   │   ├── ticket_service.py   # Incident ticket business rules
│   │   ├── service_service.py  # IT service catalog business rules
│   │   └── file_service.py     # File validation and disk storage logic
│   │
│   ├── tools/                  # Intent dispatching and tool execution
│   │   └── dispatcher.py       # Intent router mapping SLM output to business logic
│   │
│   └── prompts/                # Prompt templates for the SLM
│       └── system_prompt.txt   # Core system prompt with intent schemas & instructions
│
├── database/                   # Database schemas and DDL scripts
│   └── schema.sql              # Raw SQL reference schema with DDL and indexes
│
├── frontend/                   # React frontend application
│   ├── index.html              # HTML5 entry template
│   ├── package.json            # Node.js dependencies and scripts
│   ├── package-lock.json       # Locked dependency tree
│   ├── vite.config.js          # Vite config with backend API reverse proxy
│   │
│   └── src/
│       ├── main.jsx            # React root component mounting
│       ├── App.jsx             # Main application layout and chat coordinator
│       ├── index.css           # Premium design system, tokens, and components
│       │
│       ├── components/         # Reusable UI component library
│       │   ├── ChatInput.jsx       # Message input box with file attachment trigger
│       │   ├── ChatMessage.jsx     # User and Assistant message bubbles with markdown
│       │   ├── ConfirmDialog.jsx   # Modal confirmation dialog for destructive actions
│       │   ├── DataTable.jsx       # Dynamic tabular visualization for query results
│       │   ├── LoadingIndicator.jsx# Thinking / generating spinner
│       │   └── StatusBar.jsx       # Connectivity status indicators for Ollama & DB
│       │
│       └── services/
│           └── api.js          # HTTP client communicating with FastAPI endpoints
│
└── storage/                    # Uploaded file attachments (gitignored)
    └── .gitkeep                # Tracks empty folder structure in Git
```

---

## 🗄️ Database Information

ISLM uses a relational database schema designed to model IT infrastructure services and ITIL-aligned Service Level Management.

### Relational Schema Diagram

```
┌───────────────────────┐             ┌───────────────────────────────────┐
│        users          │             │             services              │
├───────────────────────┤             ├───────────────────────────────────┤
│ id (PK)               │◄──────┐     │ id (PK)                           │◄──────┐
│ name                  │       │     │ service_name                      │       │
│ email (UNIQUE)        │       │     │ description                       │       │
│ role                  │       │     │ status [active/maintenance/etc]   │       │
│ created_at            │       │     │ owner                             │       │
└───────────────────────┘       │     │ created_at                        │       │
            ▲                   │     └───────────────────────────────────┘       │
            │                   │                       ▲                         │
            │                   │                       │                         │
            │ 1:N               │ 1:N                   │ 1:N                     │ 1:N
            │                   │                       │                         │
┌───────────┴───────────┐       │             ┌─────────┴─────────┐               │
│         files         │       │             │        sla        │               │
├───────────────────────┤       │             ├───────────────────┤               │
│ id (PK)               │       │             │ id (PK)           │               │
│ file_name             │       │             │ service_id (FK)───┘               │
│ file_path             │       │             │ priority          │               │
│ file_type             │       │             │ response_time     │               │
│ file_size             │       │             │ resolution_time   │               │
│ uploaded_by (FK)──────┘       │             │ created_at        │               │
│ created_at            │       │             └───────────────────┘               │
└───────────────────────┘       │                                                 │
                                │                                                 │
                                └───────────────────────┬─────────────────────────┘
                                                        │
                                                        ▼
                                            ┌───────────────────────┐
                                            │        tickets        │
                                            ├───────────────────────┤
                                            │ id (PK)               │
                                            │ title                 │
                                            │ description           │
                                            │ category              │
                                            │ priority              │
                                            │ status                │
                                            │ assigned_to (FK)      │
                                            │ service_id (FK)       │
                                            │ created_at            │
                                            │ updated_at            │
                                            └───────────────────────┘
```

### Constraints & Features
- **Integrity**: Enforced Foreign Keys (`tickets` → `users`, `tickets` → `services`, `sla` → `services`, `files` → `users`).
- **Domain Constraints**: CHECK constraints ensuring valid ticket statuses (`open`, `in_progress`, `pending`, `resolved`, `closed`), categories (`network`, `server`, `database`, `application`, `security`, `hardware`), and priorities (`critical`, `high`, `medium`, `low`).
- **Indexing**: Optimized indexes on frequently queried fields (`status`, `priority`, `category`).
- **Concurrency**: Write-Ahead Logging (WAL) mode enabled for high-concurrency reading and writing.

---

## 🤖 SLM / Ollama Setup

The system is optimized for **DeepSeek-R1:1.5B**, a reasoning-focused Small Language Model that runs locally with high efficiency.

### 1. Install Ollama
Download and install Ollama for your operating system from [ollama.com](https://ollama.com/).

### 2. Pull the SLM Model
Open your terminal and pull the model:
```bash
ollama pull deepseek-r1:1.5b
```

### 3. Verify Ollama Service
Ensure Ollama is running in the background:
```bash
# Verify model installation
ollama list

# Test inference directly (optional)
ollama run deepseek-r1:1.5b "Hello, are you ready?"
```
The Ollama API will be accessible at `http://localhost:11434`.

---

## 🚀 Installation & Setup

### Prerequisites
- **Python**: Version `3.10` or higher
- **Node.js**: Version `18.0` or higher (with `npm`)
- **Ollama**: Installed and running locally
- **Git**: Installed

### Option A: One-Click Startup (Windows)

If you are on Windows, simply double-click or run:
```bat
start.bat
```
This batch script will automatically:
1. Verify Python, Node.js, and Ollama installations.
2. Pull `deepseek-r1:1.5b` if not present.
3. Install Python requirements in `backend/requirements.txt`.
4. Install frontend npm dependencies in `frontend/`.
5. Seed the database if empty.
6. Launch both backend and frontend servers in separate windows.
7. Open `http://localhost:5173` in your default browser.

---

### Option B: Manual Installation

#### 1. Clone the Repository
```bash
git clone https://github.com/fawaz165/intelligent-service-level-management-slm.git
cd islm-small-language-model
```

#### 2. Configure Environment Variables
Copy `.env.example` to create `.env`:
```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```
Default configuration values:
```env
DATABASE_URL=sqlite:///./islm.db
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:1.5b
STORAGE_PATH=./storage
MAX_FILE_SIZE_MB=10
ALLOWED_FILE_TYPES=.pdf,.doc,.docx,.txt,.csv,.xlsx,.png,.jpg,.jpeg,.log,.json,.xml
```

#### 3. Setup and Run the Backend
```bash
# Create and activate a Python virtual environment (recommended)
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

# Install backend dependencies
pip install -r backend/requirements.txt

# Seed the database with sample data
python -m backend.database.seed

# Start the FastAPI server
uvicorn backend.main:app --reload --port 8000
```
- Backend REST API: [http://localhost:8000](http://localhost:8000)
- Interactive OpenAPI Swagger Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc API Reference: [http://localhost:8000/redoc](http://localhost:8000/redoc)

#### 4. Setup and Run the Frontend
In a new terminal window:
```bash
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
- Web Application: [http://localhost:5173](http://localhost:5173)

---

## 💡 Example Usage & Natural Language Prompts

Once both servers are running and connected, you can interact with the system using plain English:

### Viewing & Querying Tickets
- *"Show all open network tickets"*
- *"List critical priority tickets currently assigned to Bob"*
- *"Find any tickets mentioning memory leak or high CPU usage"*
- *"Show me tickets in progress"*

### Creating Tickets & Services
- *"Create a high-priority network ticket titled 'Core Switch #2 Port Flapping' with description 'Packets dropping intermittently on VLAN 10'"*
- *"Add a new service called 'Auth-Service' with description 'OAuth2 and SSO provider' owned by Alice"*

### Modifying Status & Details
- *"Update ticket 3 to resolved"*
- *"Change priority of ticket 5 to critical"*
- *"Assign ticket 4 to Carol Lee"*

### Deleting Records (Safe Confirmation)
- *"Delete ticket 8"*  
  *(A modal confirmation dialog will appear asking you to confirm before the database operation executes)*

### File & Attachment Operations
- Click the **📎** icon in the chat input to upload server crash dumps, diagnostic logs, or screenshot attachments.
- *"List all uploaded log files"*
- *"Show all files uploaded by Alice"*

---

## 📡 REST API Summary

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat` | Main conversational endpoint (processes natural language via SLM) |
| `GET` | `/api/health` | Comprehensive health check (probes SQLite and Ollama status) |
| `GET` | `/api/tickets` | Query incident tickets with optional query filters |
| `POST` | `/api/tickets` | Direct programmatic ticket creation |
| `PUT` | `/api/tickets/{id}` | Update ticket properties and lifecycle status |
| `DELETE` | `/api/tickets/{id}` | Remove ticket from database |
| `GET` | `/api/services` | Retrieve list of registered IT infrastructure services |
| `POST` | `/api/services` | Register a new IT service in the catalog |
| `PUT` | `/api/services/{id}` | Update an existing IT service |
| `DELETE` | `/api/services/{id}` | Delete an IT service |
| `GET` | `/api/files` | List metadata of all stored incident attachments |
| `POST` | `/api/files/upload` | Upload diagnostic attachment files |
| `DELETE` | `/api/files/{id}` | Delete uploaded file and its metadata |

---

## 🚧 Current Project Status

> **Current Phase: Prototype & Active Development (Work in Progress)**

The project has achieved a fully functional end-to-end prototype:
- [x] Local SLM inference with Ollama and DeepSeek-R1:1.5B
- [x] Pydantic-based deterministic intent dispatching
- [x] Full CRUD operations for Tickets and Services
- [x] Relational SQLite storage with seed dataset
- [x] React 18 chat interface with streaming feedback and data tables
- [x] File upload and metadata tracking system
- [x] Destructive operation confirmation safeguards

---

## 🔮 Future Enhancements

- [ ] **Predictive SLA Breach Forecasting**: Train or fine-tune an SLM on historical resolution velocity to alert operators before SLA breach thresholds are crossed.
- [ ] **Multi-Agent Orchestration**: Implement specialized agent roles (Triage Agent, Root Cause Analysis Agent, Notification Agent).
- [ ] **Enterprise RBAC & Authentication**: Integrate OAuth2, OIDC, Active Directory, and role-based permissions (admin, technician, read-only auditor).
- [ ] **Monitoring Integrations**: Native webhooks for Prometheus Alertmanager, Grafana, Zabbix, and PagerDuty to ingest alerts as automated incident tickets.
- [ ] **RAG for Technical Runbooks**: Retrieval-Augmented Generation utilizing local vector embeddings (ChromaDB / Qdrant) to suggest resolution steps from technical runbooks.
- [ ] **Docker & Kubernetes Deployment**: Pre-built Docker Compose manifests for one-command multi-container deployment across private clouds.

---

## 📄 License

This project is licensed under the **MIT License** — feel free to use, modify, and distribute it for educational, academic, and commercial purposes.
