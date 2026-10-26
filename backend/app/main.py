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

# Initialize Database tables automatically on startup (only for local development)
try:
    if not os.getenv("VERCEL") and not settings.clean_database_url.startswith("postgresql"):
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

@app.get("/db-viewer", response_class=HTMLResponse)
def database_viewer():
    from app.database import SessionLocal
    from app.models.user import User, Profile
    from app.models.resume import Resume, JobDescription
    from app.models.taxonomy import JobRole, Skill
    from app.models.interview import PracticeSession, Interview
    import json

    db = SessionLocal()
    try:
        users = [{"id": u.id, "email": u.email, "is_admin": u.is_admin, "created_at": str(u.created_at)} for u in db.query(User).all()]
        profiles = [{"id": p.id, "user_id": p.user_id, "full_name": p.full_name, "skills": p.skills} for p in db.query(Profile).all()]
        resumes = [{"id": r.id, "user_id": r.user_id, "filename": r.filename, "created_at": str(r.created_at), "extracted_text_preview": (r.extracted_text[:200] + "...") if r.extracted_text else "None"} for r in db.query(Resume).all()]
        practices = [{"id": ps.id, "user_id": ps.user_id, "topic": ps.topic, "total_questions": ps.total_questions, "created_at": str(ps.created_at), "details": ps.answers_data} for ps in db.query(PracticeSession).all()]
        roles = [{"id": jr.id, "title": jr.title, "category": jr.category, "description": jr.description} for jr in db.query(JobRole).limit(100).all()]
    except Exception as e:
        return HTMLResponse(f"<h3>Database Query Error: {e}</h3>", status_code=500)
    finally:
        db.close()

    data_payload = {
        "users": users,
        "profiles": profiles,
        "resumes": resumes,
        "practice_sessions": practices,
        "job_roles (first 100)": roles
    }

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>IntervuAI - Live Database Table Explorer</title>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                background: #06060A;
                color: #FFFFFF;
                font-family: 'Plus Jakarta Sans', sans-serif;
                padding: 2rem;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 2rem;
                padding-bottom: 1.5rem;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }}
            .logo {{
                font-size: 1.5rem;
                font-weight: 800;
                background: linear-gradient(135deg, #8B5CF6 0%, #6366F1 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            .badge-db {{
                background: rgba(139, 92, 246, 0.15);
                border: 1px solid rgba(139, 92, 246, 0.3);
                color: #C4B5FD;
                padding: 0.35rem 0.85rem;
                border-radius: 9999px;
                font-size: 0.8rem;
                font-weight: 600;
            }}
            .nav-tabs {{
                display: flex;
                gap: 0.75rem;
                margin-bottom: 1.5rem;
                flex-wrap: wrap;
            }}
            .tab-btn {{
                background: #101017;
                border: 1px solid rgba(255, 255, 255, 0.08);
                color: #94A3B8;
                padding: 0.65rem 1.25rem;
                border-radius: 12px;
                cursor: pointer;
                font-family: inherit;
                font-size: 0.9rem;
                font-weight: 600;
                transition: all 0.2s;
            }}
            .tab-btn:hover {{
                background: #161622;
                color: #FFF;
                border-color: rgba(139, 92, 246, 0.4);
            }}
            .tab-btn.active {{
                background: #8B5CF6;
                color: #FFF;
                border-color: #8B5CF6;
                box-shadow: 0 0 20px rgba(139, 92, 246, 0.4);
            }}
            .table-container {{
                background: #0C0C12;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
                overflow: hidden;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
            }}
            .search-box {{
                padding: 1rem 1.5rem;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                background: #101017;
            }}
            .search-input {{
                width: 100%;
                background: #06060A;
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: #FFF;
                padding: 0.65rem 1rem;
                border-radius: 8px;
                font-family: inherit;
                font-size: 0.9rem;
                outline: none;
            }}
            .search-input:focus {{
                border-color: #8B5CF6;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 0.88rem;
                text-align: left;
            }}
            th {{
                background: #101017;
                color: #94A3B8;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                font-size: 0.75rem;
                padding: 1rem 1.25rem;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            }}
            td {{
                padding: 1rem 1.25rem;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                color: #E2E8F0;
                vertical-align: top;
            }}
            tr:hover td {{
                background: rgba(139, 92, 246, 0.04);
            }}
            .empty-state {{
                text-align: center;
                padding: 4rem 2rem;
                color: #64748B;
            }}
            pre {{
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.78rem;
                background: #06060A;
                padding: 0.5rem;
                border-radius: 6px;
                max-width: 500px;
                max-height: 120px;
                overflow: auto;
                color: #C4B5FD;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <div class="logo">IntervuAI Database Explorer</div>
                <div style="color: #64748B; font-size: 0.85rem; margin-top: 0.25rem;">Live Database Table Inspector</div>
            </div>
            <div>
                <span class="badge-db">Active Database: {"PostgreSQL (Neon Cloud)" if settings.clean_database_url.startswith("postgresql") else "SQLite (Local)"}</span>
            </div>
        </div>

        <div class="nav-tabs" id="tabs"></div>

        <div class="table-container">
            <div class="search-box">
                <input type="text" class="search-input" id="search" placeholder="Search table data..." oninput="filterTable()">
            </div>
            <div style="overflow-x: auto;">
                <table id="data-table">
                    <thead id="table-head"></thead>
                    <tbody id="table-body"></tbody>
                </table>
            </div>
        </div>

        <script>
            const dbData = {json.dumps(data_payload)};
            let currentTab = Object.keys(dbData)[0];

            function renderTabs() {{
                const tabsDiv = document.getElementById("tabs");
                tabsDiv.innerHTML = Object.keys(dbData).map(table => `
                    <button class="tab-btn ${{table === currentTab ? 'active' : ''}}" onclick="switchTab('${{table}}')">
                        ${{table.replace('_', ' ').toUpperCase()}} (${{dbData[table].length}})
                    </button>
                `).join('');
            }}

            function switchTab(table) {{
                currentTab = table;
                document.getElementById("search").value = "";
                renderTabs();
                renderTable(dbData[table]);
            }}

            function renderTable(rows) {{
                const thead = document.getElementById("table-head");
                const tbody = document.getElementById("table-body");
                
                if (!rows || rows.length === 0) {{
                    thead.innerHTML = "";
                    tbody.innerHTML = '<tr><td colspan="10" class="empty-state">No records found in this table.</td></tr>';
                    return;
                }}

                const cols = Object.keys(rows[0]);
                thead.innerHTML = '<tr>' + cols.map(c => `<th>${{c.replace('_', ' ')}}</th>`).join('') + '</tr>';

                tbody.innerHTML = rows.map(r => `
                    <tr>${{cols.map(c => {{
                        const val = r[c];
                        if (val === null || val === undefined) return '<td style="color:#64748B;">null</td>';
                        if (typeof val === 'object') return `<td><pre>${{JSON.stringify(val, null, 2)}}</pre></td>`;
                        if (typeof val === 'boolean') return `<td><span style="color:${{val ? '#10B981':'#EF4444'}}">${{val}}</span></td>`;
                        return `<td>${{val}}</td>`;
                    }}).join('')}}</tr>
                `).join('');
            }}

            function filterTable() {{
                const q = document.getElementById("search").value.toLowerCase();
                const rows = dbData[currentTab].filter(r => 
                    Object.values(r).some(v => String(v).toLowerCase().includes(q))
                );
                renderTable(rows);
            }}

            renderTabs();
            renderTable(dbData[currentTab]);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

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
