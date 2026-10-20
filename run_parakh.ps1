# PARAKH Windows PowerShell Runner Script
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " PARAKH: Performance & Resume Analysis for Knowledge & Hiring" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$VenvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-Not (Test-Path $VenvPython)) {
    Write-Host "[!] Virtual environment not found. Please create .venv first." -ForegroundColor Red
    exit 1
}

Write-Host "[*] Checking database and directories..." -ForegroundColor Yellow
& $VenvPython -c "from backend.app.db.database import init_db; init_db(); print('[✓] SQLite Database initialized successfully.')"

Write-Host "[*] Launching PARAKH Web Platform on http://127.0.0.1:8000 ..." -ForegroundColor Green
& $VenvPython -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
