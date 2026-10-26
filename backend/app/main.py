import sys
import os

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.routers import auth, resume, interview, dashboard

# Initialize Database tables automatically on startup
try:
    # Only run table creation / seeding on SQLite; on PostgreSQL (Neon) tables are pre-seeded
    if not settings.clean_database_url.startswith("postgresql"):
        Base.metadata.create_all(bind=engine)
        from app.database import SessionLocal
        from app.services.db_seeder import seed_database_taxonomy
        db_session = SessionLocal()
        try:
            seed_database_taxonomy(db_session)
        finally:
            db_session.close()
except Exception as e:
    print(f"Error initializing or seeding database: {e}")

app = FastAPI(
    title="AI-Powered Intelligent Interview Preparation and Performance Analysis System",
    description="A production-style system to practice interview responses, analyze resume ATS scores, and track performance",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(resume.router, prefix="/api/v1")
app.include_router(interview.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")

from fastapi.responses import HTMLResponse, JSONResponse
import os

@app.get("/", response_class=HTMLResponse)
def read_root():
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "index.html"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend", "index.html"),
        os.path.join(os.getcwd(), "frontend", "index.html"),
        os.path.join(os.getcwd(), "backend", "app", "frontend", "index.html"),
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return HTMLResponse(content=f.read(), status_code=200)
            except Exception as e:
                print(f"Error reading {path}: {e}")
    return HTMLResponse(
        content="<h1>IntervuAI API is running</h1><p>Frontend file not found at expected paths.</p>",
        status_code=200
    )

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
