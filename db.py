import os
import sqlite3

DB_PATH = os.path.join("data", "moon.db")

# DATETIME CONVENTION:
# SQLite stores datetimes as TEXT. All datetime parameters and strings must strictly
# follow ISO 8601 format: "YYYY-MM-DD HH:MM:SS" (e.g., "2026-08-15 20:00:00").


def get_connection():
    """Create and return a SQLite connection to Moon's database."""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create Moon's database and all required tables if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # Raw conversation transcript.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL CHECK (role IN ('user', 'luna')),
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Curated long-term facts about the user.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            content TEXT NOT NULL,
            importance INTEGER NOT NULL DEFAULT 3
                CHECK (importance BETWEEN 1 AND 5),
            last_referenced DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # User goals (Phase 1.5 baseline: daily, mid-term, long-term).
    # target_date and last_checked_in follow ISO 8601: "YYYY-MM-DD HH:MM:SS"
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            type TEXT NOT NULL
                CHECK (type IN ('daily', 'mid-term', 'long-term')),
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'done', 'dropped')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            target_date DATETIME,
            last_checked_in DATETIME
        )
    """)

    # Explicit user reminders.
    # remind_at follows ISO 8601: "YYYY-MM-DD HH:MM:SS"
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            remind_at DATETIME NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'sent', 'dismissed')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Luna's proactive check-in history.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS check_ins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            topic TEXT NOT NULL
                CHECK (topic IN ('goal', 'reminder', 'general', 'emotional')),
            triggered_by TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# ==========================================
# CREATE / WRITE FUNCTIONS
# ==========================================

def log_message(role: str, content: str):
    """Save a user or Luna message to the raw transcript."""
    if role not in ("user", "luna"):
        raise ValueError("role must be 'user' or 'luna'")

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO messages (role, content) VALUES (?, ?)",
            (role, content),
        )
        conn.commit()
    finally:
        conn.close()


def create_fact(category: str, content: str, importance: int = 3):
    """Store a curated long-term fact."""
    if not 1 <= importance <= 5:
        raise ValueError("importance must be between 1 and 5")

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO facts (category, content, importance)
            VALUES (?, ?, ?)
            """,
            (category, content, importance),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def normalize_goal_content(content: str) -> str:
    """Normalize goal text for exact, case-insensitive duplicate checks."""
    return " ".join(content.strip().lower().split())


class DuplicateActiveGoalError(ValueError):
    """Raised when an active goal has the same normalized content."""

    def __init__(self, goal_id: int):
        self.goal_id = goal_id
        super().__init__(f"An active goal with the same content already exists (ID {goal_id}).")


def create_goal(content: str, goal_type: str, target_date: str | None = None):
    """Create a new goal and return its ID. target_date expects 'YYYY-MM-DD HH:MM:SS'."""
    valid_types = ("daily", "mid-term", "long-term")
    if goal_type not in valid_types:
        raise ValueError(f"goal_type must be one of {valid_types}")

    conn = get_connection()
    try:
        normalized_content = normalize_goal_content(content)
        active_goals = conn.execute(
            "SELECT id, content FROM goals WHERE status = 'active'"
        ).fetchall()
        for goal in active_goals:
            if normalize_goal_content(goal["content"]) == normalized_content:
                raise DuplicateActiveGoalError(goal["id"])

        cursor = conn.execute(
            """
            INSERT INTO goals (content, type, target_date)
            VALUES (?, ?, ?)
            """,
            (content, goal_type, target_date),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def create_reminder(content: str, remind_at: str):
    """Create a pending reminder and return its ID. remind_at expects 'YYYY-MM-DD HH:MM:SS'."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO reminders (content, remind_at)
            VALUES (?, ?)
            """,
            (content, remind_at),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def create_check_in(topic: str, triggered_by: str):
    """Log a proactive Luna check-in and return its ID."""
    if topic not in ("goal", "reminder", "general", "emotional"):
        raise ValueError(
            "topic must be 'goal', 'reminder', 'general', or 'emotional'"
        )

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO check_ins (topic, triggered_by)
            VALUES (?, ?)
            """,
            (topic, triggered_by),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


# ==========================================
# READ / GET FUNCTIONS
# ==========================================

def get_recent_messages(limit: int = 20) -> list[sqlite3.Row]:
    """Retrieve the last N messages ordered chronologically."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT id, role, content, timestamp
            FROM (
                SELECT id, role, content, timestamp
                FROM messages
                ORDER BY id DESC
                LIMIT ?
            )
            ORDER BY id ASC
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        return list(rows)
    finally:
        conn.close()


def get_active_goals() -> list[sqlite3.Row]:
    """Retrieve all goals currently marked as 'active'."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT id, content, type, target_date, last_checked_in, created_at
            FROM goals
            WHERE status = 'active'
            ORDER BY created_at DESC
            """
        )
        return cursor.fetchall()
    finally:
        conn.close()


def get_pending_reminders() -> list[sqlite3.Row]:
    """Retrieve all pending reminders for scheduler polling."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT id, content, remind_at, created_at
            FROM reminders
            WHERE status = 'pending'
            ORDER BY remind_at ASC
            """
        )
        return cursor.fetchall()
    finally:
        conn.close()


def get_facts(limit: int = 10) -> list[sqlite3.Row]:
    """
    Retrieve facts ranked by importance for basic context injection.

    This is a pure read operation; it does NOT update last_referenced.
    Callers must explicitly invoke update_fact_last_referenced(fact_id)
    when a fact is actually injected into context.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT id, category, content, importance, last_referenced
            FROM facts
            ORDER BY importance DESC, created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return cursor.fetchall()
    finally:
        conn.close()


# ==========================================
# UPDATE FUNCTIONS
# ==========================================

def update_goal_status(goal_id: int, status: str) -> bool:
    """Update goal status. Returns True if updated, False if ID not found."""
    if status not in ("active", "done", "dropped"):
        raise ValueError("status must be 'active', 'done', or 'dropped'")

    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE goals SET status = ? WHERE id = ?",
            (status, goal_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def update_goal_last_checked_in(goal_id: int) -> bool:
    """Mark the current time as the last time Luna asked about this goal."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE goals SET last_checked_in = CURRENT_TIMESTAMP WHERE id = ?",
            (goal_id,),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def update_reminder_status(reminder_id: int, status: str) -> bool:
    """Update reminder status. Returns True if updated, False if ID not found."""
    if status not in ("pending", "sent", "dismissed"):
        raise ValueError("status must be 'pending', 'sent', or 'dismissed'")

    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE reminders SET status = ? WHERE id = ?",
            (status, reminder_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def update_fact_last_referenced(fact_id: int) -> bool:
    """Update the last_referenced timestamp when a fact is retrieved into context."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE facts SET last_referenced = CURRENT_TIMESTAMP WHERE id = ?",
            (fact_id,),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def fact_exists(content: str) -> bool:
    """Check if a normalized version of fact content already exists in the facts table."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT 1 FROM facts WHERE LOWER(TRIM(content)) = LOWER(TRIM(?)) LIMIT 1",
            (content.strip(),),
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Moon database initialized at: {DB_PATH}")
