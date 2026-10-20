import uvicorn
from backend.app.db.database import init_db

if __name__ == "__main__":
    print("[*] Initializing SQLite database...")
    init_db()
    print("[*] Launching PARAKH on http://127.0.0.1:8000 ...")
    uvicorn.run(
        "backend.app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
