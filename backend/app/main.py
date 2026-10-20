import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.exceptions import ParakhException
from backend.app.db.database import init_db
from backend.app.api.routes import (
    health, settings as settings_routes, resumes, interviews, answers, reports, analytics, vision
)

# Initialize database tables
init_db()

app = FastAPI(
    title=settings.APP_NAME,
    description="Performance and Resume Analysis for Knowledge and Hiring — End-to-End AI Interview Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom domain exception handler
@app.exception_handler(ParakhException)
async def parakh_exception_handler(request: Request, exc: ParakhException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "details": exc.details,
            "path": str(request.url.path)
        }
    )

# Register API Routers
app.include_router(health.router, prefix="/api")
app.include_router(settings_routes.router, prefix="/api")
app.include_router(resumes.router, prefix="/api")
app.include_router(interviews.router, prefix="/api")
app.include_router(answers.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(vision.router, prefix="/api")

# Static frontend assets directory
FRONTEND_DIR = settings.BASE_DIR / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"
TEMPLATES_DIR = FRONTEND_DIR / "templates"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    from fastapi import Response
    return Response(status_code=204)

@app.get("/")
def serve_index():
    return FileResponse(TEMPLATES_DIR / "index.html")

@app.get("/dashboard")
def serve_dashboard():
    return FileResponse(TEMPLATES_DIR / "dashboard.html")

@app.get("/resume")
def serve_resume():
    return FileResponse(TEMPLATES_DIR / "resume.html")

@app.get("/setup")
def serve_setup():
    return FileResponse(TEMPLATES_DIR / "setup.html")

@app.get("/interview")
def serve_interview():
    return FileResponse(TEMPLATES_DIR / "interview.html")

@app.get("/report")
def serve_report():
    return FileResponse(TEMPLATES_DIR / "report.html")

@app.get("/analytics")
def serve_analytics():
    return FileResponse(TEMPLATES_DIR / "analytics.html")
