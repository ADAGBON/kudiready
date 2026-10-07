# KudiReady — Architecture

Rendered PNGs of each diagram are in [`docs/diagrams/`](./diagrams).

## 1. System architecture

```mermaid
flowchart LR
  subgraph Users
    O["Business owner<br/>(phone or laptop browser)"]
    L["Loan officer<br/>(browser, no account)"]
  end

  subgraph Vercel["Vercel — global edge CDN"]
    SPA["React + TypeScript SPA<br/>static build (Vite)"]
  end

  subgraph Render["Render — Frankfurt region"]
    API["FastAPI service<br/>gunicorn + uvicorn workers<br/>Docker, non-root"]
    DB[("PostgreSQL 16<br/>managed")]
  end

  O -- "HTTPS: load app" --> SPA
  L -- "HTTPS: /p/:token" --> SPA
  SPA -- "HTTPS JSON + Bearer JWT<br/>(CORS-restricted)" --> API
  API -- "SQLAlchemy 2 / psycopg 3<br/>pooled, TLS" --> DB
```

## 2. Backend module structure

```mermaid
flowchart TB
  subgraph HTTP["HTTP layer — app/routers"]
    A[auth.py]:::r
    B[business.py]:::r
    T[transactions.py]:::r
    R[readiness.py<br/>+ share links + public view]:::r
  end
  subgraph Core["Cross-cutting — app/"]
    D[deps.py<br/>current_user / current_business]
    S[security.py<br/>bcrypt · JWT · token hashing]
    M[main.py<br/>CORS · rate limit · headers · logging · /healthz]
  end
  subgraph Domain["Domain services — app/services (pure, no I/O)"]
    C[csv_import.py<br/>parse · validate · fingerprint]
    K[categorise.py<br/>Nigerian narration rules]
    E[readiness.py<br/>indicators · 4-pillar score · gaps · capacity]
  end
  subgraph Data["Data — app/models.py + Alembic"]
    DB[(Postgres)]
  end
  A & B & T & R --> D --> S
  T --> C --> K
  R --> E
  A & B & T & R --> DB
  classDef r fill:#dfe4f3,stroke:#1e2b5c
```

## 3. Data model

```mermaid
erDiagram
  USERS ||--o| BUSINESSES : owns
  BUSINESSES ||--o{ TRANSACTIONS : records
  BUSINESSES ||--o{ SHARE_LINKS : shares

  USERS {
    uuid id PK
    string email UK
    string full_name
    string password_hash "bcrypt, cost 12"
    timestamptz created_at
  }
  BUSINESSES {
    uuid id PK
    uuid owner_id FK,UK
    string name
    string sector
    string state
    int years_operating
    int employees
    bool has_cac_registration "yes/no only"
    bool has_tin "never the number"
    bool has_business_account
    bool keeps_written_records
  }
  TRANSACTIONS {
    uuid id PK
    uuid business_id FK
    date txn_date "indexed with business_id"
    string narration
    string counterparty
    bigint amount_kobo "integer money"
    enum direction "credit | debit"
    enum category "14 categories"
    string category_source "rule | user"
    enum source "csv | manual"
    string fingerprint "UK with business_id"
  }
  SHARE_LINKS {
    uuid id PK
    uuid business_id FK
    string token_hash UK "SHA-256 only"
    string label
    timestamptz expires_at
    bool revoked
    int view_count
    json snapshot "frozen assessment"
  }
```

## 4. Statement import and scoring flow

```mermaid
sequenceDiagram
  autonumber
  actor Owner
  participant SPA as React SPA
  participant API as FastAPI
  participant P as csv_import + categorise
  participant DB as Postgres
  participant E as readiness engine

  Owner->>SPA: Choose statement.csv
  SPA->>API: POST /v1/transactions/import (multipart, JWT)
  API->>API: Check size ≤ 2 MB, type .csv
  API->>P: parse_statement(bytes)
  P-->>API: valid rows + per-row errors + fingerprints
  API->>DB: SELECT existing fingerprints
  API->>P: categorise(new rows)
  API->>DB: INSERT … ON CONFLICT DO NOTHING
  API-->>SPA: {imported, duplicates, rejected, errors}
  SPA->>API: GET /v1/readiness
  API->>DB: SELECT business's transactions
  API->>E: assess(txns, profile)
  E-->>API: indicators · score · gaps · capacity
  API-->>SPA: JSON assessment
  SPA-->>Owner: Score panel, chart, fix list
```

## 5. Delivery pipeline

```mermaid
flowchart LR
  Dev["git push / PR"] --> GH[GitHub]
  GH --> CI{{"GitHub Actions"}}
  CI --> J1["API job<br/>ruff lint + format<br/>alembic upgrade + check<br/>pytest on Postgres 16<br/>coverage ≥ 85%"]
  CI --> J2["Web job<br/>tsc typecheck<br/>vite build"]
  J1 --> J3["Docker job<br/>build prod image<br/>boot + /healthz smoke test"]
  J2 & J3 --> OK{All green?}
  OK -- "main branch" --> RD["Render auto-deploy<br/>(render.yaml blueprint)<br/>migrations on start"]
  OK -- "main branch" --> VC["Vercel auto-deploy<br/>PR preview URLs"]
  OK -- no --> X[Blocked]
```
