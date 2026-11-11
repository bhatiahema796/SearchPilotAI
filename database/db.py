
import sqlite3
from pathlib import Path
from contextlib import contextmanager

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "searchpilot.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")

    return connection


@contextmanager
def get_db():
    connection = get_connection()

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database():
    with get_db() as db:

        db.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            email TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL UNIQUE,
            client_id INTEGER NOT NULL,
            website_url TEXT NOT NULL,
            category TEXT,
            country TEXT,
            audience TEXT,
            services TEXT,
            seo_goals TEXT,
            competitors TEXT,
            status TEXT NOT NULL DEFAULT 'New Project',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL UNIQUE,
            project_id TEXT NOT NULL,
            employee TEXT NOT NULL,
            description TEXT NOT NULL,
            input_data TEXT,
            status TEXT NOT NULL DEFAULT 'Pending',
            output TEXT,
            evidence TEXT,
            error TEXT,
            created_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            FOREIGN KEY (project_id)
                REFERENCES projects(project_id)
        );

        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            agent_name TEXT NOT NULL,
            task_performed TEXT NOT NULL,
            output_status TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            file_path TEXT,
            qa_status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL,
            FOREIGN KEY (project_id)
                REFERENCES projects(project_id)
        );

        CREATE TABLE IF NOT EXISTS website_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            page_url TEXT NOT NULL,
            evidence_type TEXT NOT NULL,
            evidence_value TEXT,
            source_status TEXT,
            collected_at TEXT NOT NULL,
            FOREIGN KEY (project_id)
                REFERENCES projects(project_id)
        );

        CREATE TABLE IF NOT EXISTS email_deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            recipient TEXT NOT NULL,
            subject TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            message_id TEXT,
            error TEXT,
            created_at TEXT NOT NULL,
            sent_at TEXT,
            FOREIGN KEY (project_id)
                REFERENCES projects(project_id)
        );

        CREATE INDEX IF NOT EXISTS idx_tasks_project
        ON tasks(project_id);

        CREATE INDEX IF NOT EXISTS idx_logs_project
        ON activity_logs(project_id);

        CREATE INDEX IF NOT EXISTS idx_email_project
        ON email_deliveries(project_id);
        """)

    print("SearchPilot AI database initialized successfully.")
    print(f"Database location: {DB_PATH}")


if __name__ == "__main__":
    initialize_database()
