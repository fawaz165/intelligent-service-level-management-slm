# ISLM — Intelligent Service Level Management

**Natural-language IT Service Management powered by a local DeepSeek-R1:1.5B model.**

A working prototype that lets you manage IT service tickets, services, SLAs, and files through a ChatGPT-like chat interface. The local Small Language Model (SLM) understands your natural-language requests and translates them into safe, validated database operations — never executing raw SQL from the model.

---

## Architecture

```
User → React Chat UI (port 5173)
         ↓ HTTP/REST
       FastAPI Backend (port 8000)
         ├── HTTP → Ollama (port 11434) → DeepSeek-R1:1.5B
         ├── SQLAlchemy → SQLite (islm.db)
         └── Filesystem → storage/
```

### Security Architecture
```
LLM → Structured JSON Intent → Backend Validation → Parameterized SQL → Database
```
The LLM **never** generates or executes SQL directly.

---

## Tech Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Frontend   | React + Vite + Vanilla CSS          |
| Backend    | Python + FastAPI                    |
| Database   | SQLite (SQLAlchemy ORM)             |
| Local SLM  | DeepSeek-R1:1.5B via Ollama         |
| File Store | Local filesystem (`storage/`)       |

---

## Prerequisites

1. **Python 3.10+** — [python.org](https://www.python.org/downloads/)
2. **Node.js 18+** — [nodejs.org](https://nodejs.org/)
3. **Ollama** — [ollama.com](https://ollama.com/)

---

## Quick Start

### 1. Install & Pull the Model

```bash
# Install Ollama (if not already installed), then:
ollama pull deepseek-r1:1.5b
```

Make sure Ollama is running (it starts automatically after install).

### 2. Backend Setup

```bash
# From the project root
cd backend
pip install -r requirements.txt

# Seed the database with sample data
cd ..
python -m backend.database.seed

# Start the backend server
uvicorn backend.main:app --reload --port 8000
```

The backend will be available at `http://localhost:8000`.  
API documentation at `http://localhost:8000/docs`.

### 3. Frontend Setup

```bash
# In a new terminal, from the project root
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

### 4. Open the App

Navigate to **http://localhost:5173** in your browser.

---

## Features

### Natural Language CRUD
Talk to the system in plain English:

| Action | Example |
|--------|---------|
| **Read** | "Show all open network tickets" |
| **Create** | "Create a high-priority ticket called Router failure" |
| **Update** | "Change ticket 5 status to resolved" |
| **Delete** | "Delete ticket 10" (with confirmation) |
| **Search** | "Find tickets about database" |
| **Files** | "Show all PDF files" |

### Chat Interface
- User/AI message distinction with avatars
- Structured data tables for query results
- Confirmation dialogs for destructive operations
- File upload via 📎 button
- System status bar (Ollama, Database, Model)
- Clear chat button
- Example queries on welcome screen

### DBMS Concepts Demonstrated
- Relational schema (5 normalized tables)
- Primary keys (auto-increment)
- Foreign keys (tickets → users, tickets → services, sla → services, files → users)
- CHECK constraints (status, category, priority enums)
- UNIQUE constraints (user email)
- Indexes (ticket status, category, priority)
- Transactions (SQLAlchemy session management)
- Parameterized queries (ORM prevents SQL injection)

### Security
- No raw LLM-generated SQL execution
- Input validation and normalization
- File type whitelist
- File size limits (10 MB)
- Safe file paths (no directory traversal)
- Confirmation required for DELETE operations

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Natural-language chat interface |
| `GET` | `/api/health` | System health status |
| `GET` | `/api/tickets` | List tickets (with filters) |
| `POST` | `/api/tickets` | Create a ticket |
| `PUT` | `/api/tickets/{id}` | Update a ticket |
| `DELETE` | `/api/tickets/{id}` | Delete a ticket |
| `GET` | `/api/services` | List services |
| `POST` | `/api/services` | Create a service |
| `PUT` | `/api/services/{id}` | Update a service |
| `DELETE` | `/api/services/{id}` | Delete a service |
| `GET` | `/api/files` | List files |
| `POST` | `/api/files/upload` | Upload a file |
| `DELETE` | `/api/files/{id}` | Delete a file |

---

## Database Schema

```
users (id, name, email, role, created_at)
  ├── 1:N → tickets (assigned_to)
  └── 1:N → files (uploaded_by)

services (id, service_name, description, status, owner, created_at)
  ├── 1:N → tickets (service_id)
  └── 1:N → sla (service_id)

tickets (id, title, description, category, priority, status, assigned_to, service_id, created_at, updated_at)

sla (id, service_id, priority, response_time, resolution_time, created_at)

files (id, file_name, file_path, file_type, file_size, uploaded_by, created_at)
```

---

## Project Structure

```
islm-project/
├── frontend/                  # React + Vite
│   ├── src/
│   │   ├── components/        # UI components
│   │   │   ├── ChatMessage.jsx
│   │   │   ├── ChatInput.jsx
│   │   │   ├── StatusBar.jsx
│   │   │   ├── ConfirmDialog.jsx
│   │   │   ├── DataTable.jsx
│   │   │   └── LoadingIndicator.jsx
│   │   ├── services/
│   │   │   └── api.js         # Backend API client
│   │   ├── App.jsx            # Main application
│   │   ├── main.jsx           # Entry point
│   │   └── index.css          # Design system
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
│
├── backend/                   # Python + FastAPI
│   ├── main.py                # App entry point
│   ├── config.py              # Configuration
│   ├── api/                   # REST API routes
│   │   ├── chat.py
│   │   ├── tickets.py
│   │   ├── services.py
│   │   ├── files.py
│   │   └── health.py
│   ├── database/              # Data layer
│   │   ├── connection.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── seed.py
│   ├── services/              # Business logic
│   │   ├── llm_service.py
│   │   ├── ticket_service.py
│   │   ├── service_service.py
│   │   └── file_service.py
│   ├── tools/
│   │   └── dispatcher.py      # Intent → service routing
│   ├── prompts/
│   │   └── system_prompt.txt  # DeepSeek-R1 system prompt
│   └── requirements.txt
│
├── database/
│   └── schema.sql             # Reference SQL schema
├── storage/                   # Uploaded files
├── .env                       # Configuration
└── README.md
```

---

## Demonstration Walkthrough

1. **Open the app** at http://localhost:5173
2. **Check status bar** — verify Ollama and Database show "Connected"
3. **"Show all open network tickets"** → See filtered ticket table
4. **"Create a high-priority database ticket called Database connection failure"** → Ticket created
5. **"Change ticket 2 status to resolved"** → Ticket updated
6. **"Delete ticket 12"** → Confirmation dialog appears
7. **Upload a file** via 📎 button → File metadata stored
8. **"Show all uploaded files"** → File listing table

---

## Networking Concepts

- **HTTP/REST**: Frontend ↔ Backend communication over HTTP
- **Client-Server Architecture**: React client, FastAPI server
- **Localhost Networking**: All services on `127.0.0.1` (ports 5173, 8000, 11434)
- **API Endpoints**: RESTful resource-based routing
- **Request/Response Flow**: JSON payloads over HTTP POST/GET/PUT/DELETE
- **Proxy**: Vite dev proxy forwards `/api` requests to backend
- **Database Connectivity**: SQLAlchemy connects to SQLite via filesystem

---

## License

Educational project — MIT License.
