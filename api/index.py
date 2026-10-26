import os
import sys
import traceback

# Ensure root, backend, and app directories are in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
backend_dir = os.path.join(root_dir, "backend")

for path in [root_dir, backend_dir, os.path.join(backend_dir, "app")]:
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    from app.main import app
except Exception as e:
    err_tb = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    
    app = FastAPI(title="IntervuAI - Error Diagnostic")
    
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def catch_all(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "FastAPI failed to start on Vercel",
                "details": str(e),
                "traceback": err_tb,
                "sys_path": sys.path,
                "env_vars_present": {
                    "DATABASE_URL": bool(os.getenv("DATABASE_URL")),
                    "GEMINI_API_KEY": bool(os.getenv("GEMINI_API_KEY")),
                    "JWT_SECRET": bool(os.getenv("JWT_SECRET")),
                    "DEMO_MODE": os.getenv("DEMO_MODE")
                }
            }
        )
