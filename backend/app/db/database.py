from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.core.config import settings

# SQLite connection with thread safety and WAL mode for high concurrency
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# Enable foreign key constraints and WAL on SQLite connections
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in settings.DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """FastAPI Dependency for database session injection."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def migrate_sqlite_schema(db_engine):
    """Safely adds newly defined columns to existing SQLite tables if not present."""
    if "sqlite" not in settings.DATABASE_URL:
        return

    table_columns = {
        "interviews": [
            ("question_mix", "TEXT DEFAULT 'mixed'")
        ],
        "candidate_profiles": [
            ("ats_score", "REAL DEFAULT 0.0"),
            ("ats_breakdown", "TEXT DEFAULT '{}'"),
            ("contact_links", "TEXT DEFAULT '{}'"),
            ("cv_improvement_tips", "TEXT DEFAULT '[]'"),
            ("skill_depth_matrix", "TEXT DEFAULT '{}'")
        ],
        "interview_questions": [
            ("question_type", "TEXT DEFAULT 'SPOKEN'"),
            ("options", "TEXT DEFAULT '[]'"),
            ("correct_option", "TEXT DEFAULT NULL"),
            ("code_snippet", "TEXT DEFAULT NULL"),
            ("language", "TEXT DEFAULT 'python'"),
            ("explanation", "TEXT DEFAULT NULL"),
            ("examples", "TEXT DEFAULT '[]'"),
            ("test_cases", "TEXT DEFAULT '[]'"),
            ("constraints", "TEXT DEFAULT '[]'")
        ],
        "answers": [
            ("browser_transcript", "TEXT DEFAULT NULL"),
            ("selected_option", "TEXT DEFAULT NULL"),
            ("code_submission", "TEXT DEFAULT NULL")
        ],
        "assessment_reports": [
            ("vision_analytics", "TEXT DEFAULT '{}'"),
            ("audio_analytics", "TEXT DEFAULT '{}'")
        ]
    }

    with db_engine.connect() as conn:
        for table, cols in table_columns.items():
            try:
                result = conn.exec_driver_sql(f"PRAGMA table_info({table})")
                existing_cols = {row[1] for row in result.fetchall()}
                if not existing_cols:
                    continue
                for col_name, col_def in cols:
                    if col_name not in existing_cols:
                        conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
                        conn.commit()
            except Exception:
                pass

def init_db():
    """Initializes tables and ensures all newly added columns exist."""
    Base.metadata.create_all(bind=engine)
    migrate_sqlite_schema(engine)

