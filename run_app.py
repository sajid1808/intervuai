"""
IntervuAI - Unified Single-File Launcher
Run with: python run_app.py
"""
import sys
import os
import uvicorn

# Ensure the backend directory is in the python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(current_dir, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app
from app.config import settings

if __name__ == "__main__":
    print("=" * 60)
    print(" Starting IntervuAI Standalone Server...")
    print(f" Web App URL: http://127.0.0.1:{settings.PORT}")
    print(f" API Docs:    http://127.0.0.1:{settings.PORT}/docs")
    print("=" * 60)
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
