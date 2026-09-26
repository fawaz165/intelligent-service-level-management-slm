-- ═══════════════════════════════════════════════════════════════════════
-- ISLM Database Schema (Reference)
-- Demonstrates: Primary keys, Foreign keys, Constraints, Indexes,
--               Normalization, Relationships
-- ═══════════════════════════════════════════════════════════════════════

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR(120)    NOT NULL,
    email       VARCHAR(255)    NOT NULL UNIQUE,
    role        VARCHAR(50)     NOT NULL DEFAULT 'technician',
    created_at  DATETIME        DEFAULT CURRENT_TIMESTAMP
);

-- Services table
CREATE TABLE IF NOT EXISTS services (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name    VARCHAR(200)    NOT NULL,
    description     TEXT,
    status          VARCHAR(30)     NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active','inactive','maintenance','deprecated')),
    owner           VARCHAR(120),
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP
);

-- Tickets table  (FK → users, FK → services)
CREATE TABLE IF NOT EXISTS tickets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           VARCHAR(300)    NOT NULL,
    description     TEXT,
    category        VARCHAR(50)     NOT NULL DEFAULT 'Application'
                    CHECK (category IN ('Network','Database','Server','Application','Security','Hardware')),
    priority        VARCHAR(20)     NOT NULL DEFAULT 'medium'
                    CHECK (priority IN ('low','medium','high','critical')),
    status          VARCHAR(20)     NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open','in_progress','resolved','closed')),
    assigned_to     INTEGER         REFERENCES users(id) ON DELETE SET NULL,
    service_id      INTEGER         REFERENCES services(id) ON DELETE SET NULL,
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        DEFAULT CURRENT_TIMESTAMP
);

-- Indexes on frequently queried ticket columns
CREATE INDEX IF NOT EXISTS ix_tickets_status   ON tickets(status);
CREATE INDEX IF NOT EXISTS ix_tickets_category ON tickets(category);
CREATE INDEX IF NOT EXISTS ix_tickets_priority ON tickets(priority);

-- SLA table  (FK → services)
CREATE TABLE IF NOT EXISTS sla (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id      INTEGER         NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    priority        VARCHAR(20)     NOT NULL,
    response_time   VARCHAR(50)     NOT NULL,
    resolution_time VARCHAR(50)     NOT NULL,
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP
);

-- Files table  (FK → users)
CREATE TABLE IF NOT EXISTS files (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name       VARCHAR(255)    NOT NULL,
    file_path       VARCHAR(500)    NOT NULL,
    file_type       VARCHAR(20)     NOT NULL,
    file_size       INTEGER         NOT NULL,
    uploaded_by     INTEGER         REFERENCES users(id) ON DELETE SET NULL,
    created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP
);
