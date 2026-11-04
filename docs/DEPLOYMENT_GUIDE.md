# Production Deployment & Operations Runbook
**AI-Powered Student Achievement Intelligence Platform — Member 3**

---

## 1. Local Quick-Start Guide

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Git

### Quick Setup Steps
```bash
# 1. Switch to Member 3 working branch
git checkout feature/recommendation-platform

# 2. Install Python dependencies
pip install -r requirements.txt
pip install -r requirements-m3.txt

# 3. Seed demo database with sample users and canonical opportunities
python -m scripts.seed_demo

# 4. Run FastAPI backend server (Port 8000)
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# 5. In a separate terminal, run React frontend (Port 5173)
cd frontend
npm install
npm run dev

# (Alternative) Run Streamlit multi-page dashboard (Port 8501)
streamlit run frontend/streamlit_app.py
```

- **Backend API Swagger Documentation:** `http://localhost:8000/docs`
- **React Frontend Application:** `http://localhost:5173`
- **Streamlit Interactive Demo:** `http://localhost:8501`

---

## 2. Docker & Multi-Container Deployment

To deploy the entire production stack (PostgreSQL + Redis + FastAPI Backend + React Nginx Frontend) with a single command:

```bash
# Build and launch production containers
docker compose up --build -d

# Verify container health status
docker compose ps
```

### Services Deployed
| Service Name | Container Name | Port | Description |
| :--- | :--- | :--- | :--- |
| `backend` | `student_intel_backend` | `8000` | FastAPI REST API & Recommendation Engine |
| `frontend` | `student_intel_frontend` | `80` | Production React build served via Nginx |
| `db` | `student_intel_postgres` | `5432` | PostgreSQL 15 relational database |
| `redis` | `student_intel_redis` | `6379` | In-memory cache & rate limiter |

---

## 3. Database Migration Runbook (Alembic)

```bash
# Apply pending schema migrations
alembic upgrade head

# Rollback last migration step
alembic downgrade -1
```

---

## 4. Production Smoke Testing & Verification

Run the automated smoke test script against running services:
```bash
python scripts/smoke_test.py
```

The smoke test validates:
- [x] Liveness probe `/health` returns HTTP 200 with status `UP`.
- [x] Authentication `/api/v1/auth/login` issues valid JWT token.
- [x] Opportunity catalog `/api/v1/opportunities` returns $N \ge 500$ records.
- [x] Personalized recommendations `/api/v1/recommendations/{id}` returns top-10 ranked items with grounded explanations.
- [x] Transcript generation `/api/v1/reports/transcript/{id}` returns non-empty `%PDF-1.4` stream.
