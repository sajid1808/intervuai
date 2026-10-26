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

from fastapi.responses import FileResponse
import os

@app.get("/")
def read_root():
    frontend_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "frontend",
        "index.html"
    )
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {
        "message": "AI-Powered Interview Prep API is running",
        "demo_mode": settings.DEMO_MODE,
        "database_connected": True
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
