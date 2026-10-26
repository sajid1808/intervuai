# IntervuAI - AI-Powered Intelligent Interview Preparation & Performance Analysis System

**IntervuAI** is a modern, full-stack career acceleration and interview preparation platform built using **FastAPI (Python)**, **React.js**, and **PostgreSQL (with SQLite local fallback)**. It integrates Generative AI (Gemini API) and deterministic evaluation algorithms to offer:
* Resume uploading & parsing (PDF / DOCX)
* General & Job-Specific ATS Compatibility scoring (0-100)
* Missing Keyword & Skill Gap Analysis
* 390+ Role Taxonomy across 18 Engineering & Tech Domains
* Dynamic Multi-Question Practice Drills with Voice Dictation & Real-Time Scoring
* Accurate Key Concepts Addressed vs Missing Concept Gap Analysis
* Full Mock Interview Simulator with Adaptive Question Engine & STAR Method Grading
* Longitudinal Analytics & Performance dashboards
* Admin analytics panel

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have **Python 3.10+** installed on your system.

### 2. Environment Configurations
Rename the `.env.example` in the backend to `.env` or create it with:
```ini
DATABASE_URL=sqlite:///./interview_prep.db
JWT_SECRET=4f63c87e83dbbfa20d6f45c85023901b0b5cd30a3f9e8a719c8f8b89d4d5e6a1
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=11520
GEMINI_API_KEY=your_gemini_api_key_here
DEMO_MODE=False
PORT=8000
HOST=127.0.0.1
```
*Note: If `GEMINI_API_KEY` is omitted or invalid, the backend automatically operates in **Demo Mode**, yielding rich pre-seeded mock questions and evaluation analysis.*

### 3. Backend Setup & Run
Open your terminal in the `backend/` directory:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install email-validator

# Run the FastAPI server
python -m uvicorn app.main:app --reload
```
Once uvicorn is running, the server is available at **`http://127.0.0.1:8000`**.

### 4. Running the Frontend SPA
The React.js frontend is served **directly from the FastAPI server root** for a zero-installation local setup!
Simply open your web browser to:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 📁 Folder Structure

```text
interview_prep_system/
├── backend/
│   ├── app/
│   │   ├── config.py            # Environment configurations
│   │   ├── database.py          # SQLAlchemy session setup
│   │   ├── main.py              # FastAPI app instance
│   │   ├── security.py          # Hashing & JWT functions
│   │   ├── models/              # Database Schema Models
│   │   ├── schemas/             # Pydantic Schemas
│   │   ├── routers/             # API Router Handlers
│   │   ├── services/            # ATS Scorers, parsers, AI wrappers
│   │   └── tests/               # Pytest suites
│   ├── requirements.txt
│   └── .env
├── frontend/
│   └── index.html               # React.js SPA (Babel, Axios, CSS)
└── README.md
```

---

## 🧪 Running Pytest Suite
To verify core database, authentication, profile sync, and ATS grading logic:
```bash
cd backend/
.\venv\Scripts\python -m pytest app/tests
```
All tests should pass.
