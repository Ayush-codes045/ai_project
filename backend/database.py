import json
import sqlite3
from datetime import datetime
from pathlib import Path
from models.schemas import TaskHistoryItem

DB_PATH = Path(__file__).parent / "tasks.db"


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database tables."""
    conn = get_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS task_history (
                task_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                language TEXT DEFAULT 'python',
                result_json TEXT,
                files_count INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0.0,
                time_taken REAL DEFAULT 0.0,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def save_task(task_id: str, description: str, status: str, language: str, result: dict):
    """Save a completed task to history."""
    conn = get_db()
    data = result.get("data", {})
    metrics = data.get("metrics", {})
    try:
        conn.execute("""
            INSERT OR REPLACE INTO task_history
            (task_id, description, status, language, result_json, files_count, total_tokens, cost_usd, time_taken, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task_id,
            description,
            status,
            language,
            json.dumps(result),
            metrics.get("files_generated", 0),
            metrics.get("total_tokens", 0),
            metrics.get("total_cost_usd", 0.0),
            metrics.get("time_taken_seconds", 0.0),
            datetime.now().isoformat(),
        ))
        conn.commit()
    finally:
        conn.close()


def get_task_history(limit: int = 20) -> list[TaskHistoryItem]:
    """Get recent task history."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM task_history ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    finally:
        conn.close()

    return [
        TaskHistoryItem(
            task_id=row["task_id"],
            description=row["description"],
            status=row["status"],
            language=row["language"],
            files_count=row["files_count"],
            total_tokens=row["total_tokens"],
            cost_usd=row["cost_usd"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def get_task_result(task_id: str) -> dict | None:
    """Get full result for a specific task."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT result_json FROM task_history WHERE task_id = ?", (task_id,)
        ).fetchone()
    finally:
        conn.close()

    if row and row["result_json"]:
        return json.loads(row["result_json"])
    return None


# Initialize on import
init_db()