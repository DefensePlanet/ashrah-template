"""SQLite database operations for the voice recording pipeline.

Follows the WAL-mode, busy_timeout, row_factory pattern from
Catalyst's file-organizer/database.py.
"""

import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple


def get_connection(db_path: str) -> sqlite3.Connection:
    """Open (or create) the SQLite database and ensure schema exists.

    Args:
        db_path: Absolute path to the database file.

    Returns:
        sqlite3.Connection with WAL mode, busy_timeout, and row_factory set.
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    _create_schema(conn)
    return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't already exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS recordings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            source_path     TEXT    NOT NULL UNIQUE,
            source_app      TEXT    NOT NULL DEFAULT '',
            file_hash       TEXT    NOT NULL DEFAULT '',
            file_size       INTEGER NOT NULL DEFAULT 0,
            duration_secs   REAL    NOT NULL DEFAULT 0.0,
            recorded_at     TEXT    NOT NULL DEFAULT '',
            discovered_at   TEXT    NOT NULL DEFAULT '',
            denoised_path   TEXT    NOT NULL DEFAULT '',
            transcript      TEXT    NOT NULL DEFAULT '',
            word_count      INTEGER NOT NULL DEFAULT 0,
            category        TEXT    NOT NULL DEFAULT '',
            confidence      REAL    NOT NULL DEFAULT 0.0,
            summary         TEXT    NOT NULL DEFAULT '',
            speakers        INTEGER NOT NULL DEFAULT 1,
            diarized        INTEGER NOT NULL DEFAULT 0,
            output_dir      TEXT    NOT NULL DEFAULT '',
            status          TEXT    NOT NULL DEFAULT 'discovered',
            error_message   TEXT    NOT NULL DEFAULT '',
            retry_count     INTEGER NOT NULL DEFAULT 0,
            processed_at    TEXT    NOT NULL DEFAULT '',
            finder_tagged   INTEGER NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_recordings_status ON recordings(status);
        CREATE INDEX IF NOT EXISTS idx_recordings_source_app ON recordings(source_app);
        CREATE INDEX IF NOT EXISTS idx_recordings_category ON recordings(category);
        CREATE INDEX IF NOT EXISTS idx_recordings_file_hash ON recordings(file_hash);
        CREATE INDEX IF NOT EXISTS idx_recordings_recorded_at ON recordings(recorded_at);

        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at      TEXT    NOT NULL DEFAULT '',
            finished_at     TEXT    NOT NULL DEFAULT '',
            mode            TEXT    NOT NULL DEFAULT '',
            files_found     INTEGER NOT NULL DEFAULT 0,
            files_processed INTEGER NOT NULL DEFAULT 0,
            files_errored   INTEGER NOT NULL DEFAULT 0,
            duration_secs   REAL    NOT NULL DEFAULT 0.0
        );
    """)
    conn.commit()


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def upsert_recording(conn: sqlite3.Connection, info: dict) -> int:
    """Insert or update a recording record.

    Args:
        conn: Database connection.
        info: Dict with keys: source_path, source_app, file_hash, file_size,
              recorded_at. Optional: duration_secs.

    Returns:
        The row id of the inserted/updated record.
    """
    now = datetime.now().isoformat()
    params = {
        "source_path": info["source_path"],
        "source_app": info.get("source_app", ""),
        "file_hash": info.get("file_hash", ""),
        "file_size": info.get("file_size", 0),
        "duration_secs": info.get("duration_secs", 0.0),
        "recorded_at": info.get("recorded_at", ""),
        "discovered_at": now,
    }

    conn.execute("""
        INSERT INTO recordings (source_path, source_app, file_hash, file_size,
                                duration_secs, recorded_at, discovered_at, status)
        VALUES (:source_path, :source_app, :file_hash, :file_size,
                :duration_secs, :recorded_at, :discovered_at, 'discovered')
        ON CONFLICT(source_path) DO UPDATE SET
            file_hash = excluded.file_hash,
            file_size = excluded.file_size,
            discovered_at = excluded.discovered_at
    """, params)
    conn.commit()

    row = conn.execute(
        "SELECT id FROM recordings WHERE source_path = ?",
        (info["source_path"],),
    ).fetchone()
    return row["id"] if row else -1


def get_unprocessed(
    conn: sqlite3.Connection,
    limit: int = 0,
    source_app: Optional[str] = None,
    max_retries: int = 3,
) -> List[dict]:
    """Get recordings that need processing.

    Returns recordings with status in ('discovered', 'denoised', 'transcribed',
    'categorized', 'written', 'error') that haven't exceeded max retries.

    Args:
        conn: Database connection.
        limit: Max number of records to return (0 = all).
        source_app: Filter by source app name.
        max_retries: Max retry_count before considering a file as failed.

    Returns:
        List of recording dicts.
    """
    processable_statuses = (
        "discovered", "denoised", "transcribed", "categorized", "written", "error"
    )
    placeholders = ",".join("?" for _ in processable_statuses)
    query = f"""
        SELECT * FROM recordings
        WHERE status IN ({placeholders})
        AND retry_count < ?
    """
    params: list = list(processable_statuses) + [max_retries]

    if source_app:
        query += " AND source_app = ?"
        params.append(source_app)

    query += " ORDER BY recorded_at ASC"

    if limit > 0:
        query += " LIMIT ?"
        params.append(limit)

    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def update_status(
    conn: sqlite3.Connection,
    source_path: str,
    status: str,
    **kwargs,
) -> None:
    """Update a recording's status and optional fields.

    Args:
        conn: Database connection.
        source_path: The unique source path identifying the recording.
        status: New status value.
        **kwargs: Additional columns to update (e.g., transcript, category, etc.).
    """
    # Allowlist of valid column names to prevent SQL injection
    VALID_COLUMNS = frozenset({
        "source_app", "file_hash", "file_size", "duration_secs", "recorded_at",
        "discovered_at", "denoised_path", "transcript", "word_count",
        "category", "confidence", "summary", "speakers", "diarized",
        "output_dir", "error_message", "retry_count", "processed_at",
        "finder_tagged",
    })

    sets = ["status = ?"]
    params: list = [status]

    for key, value in kwargs.items():
        if key not in VALID_COLUMNS:
            raise ValueError(f"Invalid column name: {key!r}")
        sets.append(f"{key} = ?")
        params.append(value)

    params.append(source_path)

    conn.execute(
        f"UPDATE recordings SET {', '.join(sets)} WHERE source_path = ?",
        params,
    )
    conn.commit()


def increment_retry(conn: sqlite3.Connection, source_path: str, error_message: str) -> int:
    """Increment retry count and store error message.

    Args:
        conn: Database connection.
        source_path: The unique source path.
        error_message: Error description.

    Returns:
        New retry count.
    """
    conn.execute("""
        UPDATE recordings
        SET retry_count = retry_count + 1,
            error_message = ?,
            status = 'error'
        WHERE source_path = ?
    """, (error_message, source_path))
    conn.commit()

    row = conn.execute(
        "SELECT retry_count FROM recordings WHERE source_path = ?",
        (source_path,),
    ).fetchone()
    return row["retry_count"] if row else 0


def mark_failed(conn: sqlite3.Connection, source_path: str) -> None:
    """Mark a recording as permanently failed (exceeded max retries)."""
    conn.execute(
        "UPDATE recordings SET status = 'failed' WHERE source_path = ?",
        (source_path,),
    )
    conn.commit()


def recording_exists(conn: sqlite3.Connection, source_path: str) -> bool:
    """Check if a recording already exists in the database."""
    row = conn.execute(
        "SELECT 1 FROM recordings WHERE source_path = ?",
        (source_path,),
    ).fetchone()
    return row is not None


def get_recording(conn: sqlite3.Connection, source_path: str) -> Optional[dict]:
    """Get a single recording by source path."""
    row = conn.execute(
        "SELECT * FROM recordings WHERE source_path = ?",
        (source_path,),
    ).fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Pipeline run tracking
# ---------------------------------------------------------------------------

def create_pipeline_run(conn: sqlite3.Connection, mode: str) -> int:
    """Create a new pipeline run record.

    Args:
        conn: Database connection.
        mode: Run mode (e.g., 'process', 'watch', 'reprocess').

    Returns:
        The run id.
    """
    now = datetime.now().isoformat()
    cursor = conn.execute(
        "INSERT INTO pipeline_runs (started_at, mode) VALUES (?, ?)",
        (now, mode),
    )
    conn.commit()
    return cursor.lastrowid


def finish_pipeline_run(
    conn: sqlite3.Connection,
    run_id: int,
    files_found: int,
    files_processed: int,
    files_errored: int,
    duration_secs: float,
) -> None:
    """Mark a pipeline run as completed."""
    now = datetime.now().isoformat()
    conn.execute("""
        UPDATE pipeline_runs
        SET finished_at = ?, files_found = ?, files_processed = ?,
            files_errored = ?, duration_secs = ?
        WHERE id = ?
    """, (now, files_found, files_processed, files_errored, duration_secs, run_id))
    conn.commit()


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def get_stats(conn: sqlite3.Connection) -> dict:
    """Get pipeline statistics.

    Returns:
        Dict with total counts, category breakdown, and last run info.
    """
    # Total counts by status
    status_rows = conn.execute("""
        SELECT status, COUNT(*) as cnt
        FROM recordings
        GROUP BY status
    """).fetchall()
    status_counts = {r["status"]: r["cnt"] for r in status_rows}

    total = sum(status_counts.values())
    complete = status_counts.get("complete", 0)
    pending = sum(
        status_counts.get(s, 0)
        for s in ("discovered", "denoised", "transcribed", "categorized", "written")
    )
    errors = status_counts.get("error", 0)
    failed = status_counts.get("failed", 0)

    # Category breakdown
    cat_rows = conn.execute("""
        SELECT category, COUNT(*) as cnt
        FROM recordings
        WHERE category != ''
        GROUP BY category
        ORDER BY cnt DESC
    """).fetchall()
    categories = {r["category"]: r["cnt"] for r in cat_rows}

    # Last pipeline run
    last_run = conn.execute("""
        SELECT * FROM pipeline_runs
        ORDER BY started_at DESC
        LIMIT 1
    """).fetchone()

    return {
        "total": total,
        "complete": complete,
        "pending": pending,
        "errors": errors,
        "failed": failed,
        "status_counts": status_counts,
        "categories": categories,
        "last_run": dict(last_run) if last_run else None,
    }
