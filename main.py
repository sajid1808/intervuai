import os
import sys
import traceback

root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, "backend")

for p in [root_dir, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from app.main import app
except Exception as exc:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    
    app = FastAPI(title="IntervuAI - Diagnostics")
    err_trace = traceback.format_exc()
    
    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    def diagnostic_fallback(full_path: str = ""):
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>IntervuAI - Diagnostic Info</title></head>
            <body style="background:#06060A; color:#f87171; font-family:monospace; padding:30px;">
                <h1 style="color:#a78bfa;">IntervuAI - Server Diagnostics</h1>
                <p style="color:#94a3b8;">A startup error occurred while initializing FastAPI:</p>
                <pre style="background:#0f172a; padding:20px; border-radius:8px; border:1px solid #1e293b; color:#fca5a5; overflow-x:auto;">{err_trace}</pre>
                <div style="margin-top:20px; color:#64748b; font-size:12px;">
                    <p>DATABASE_URL configured: {bool(os.getenv('DATABASE_URL'))}</p>
                    <p>VERCEL environment: {os.getenv('VERCEL')}</p>
                </div>
            </body>
            </html>
            """,
            status_code=200
        )
