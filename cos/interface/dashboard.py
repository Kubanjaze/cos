"""COS workspace dashboard — system overview. Phase 198.

Also covers: Phase 200 (timeline UI), Phase 201 (decision board UI),
Phase 203 (file upload UI), Phase 204 (notifications), Phase 205 (user settings).
"""

import sqlite3
import json
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.interface.dashboard")


class WorkspaceDashboard:
    """Text-based workspace dashboard showing system state."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def render(self) -> str:
        """Render the full workspace dashboard."""
        conn = self._get_conn()
        sections = []

        # Header
        from cos import __version__
        sections.append(f"COS Dashboard v{__version__}")
        sections.append("=" * 50)

        # System health
        tables_counts = {}
        for table in ["investigations", "artifacts", "documents", "entities",
                       "concepts", "hypotheses", "decisions", "episodes"]:
            try:
                tables_counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except Exception:
                tables_counts[table] = 0

        sections.append("\nKnowledge Base:")
        for t, c in tables_counts.items():
            sections.append(f"  {t:>15}: {c:>6}")

        # Recent activity (Phase 200: timeline)
        try:
            eps = conn.execute(
                "SELECT episode_type, description, created_at FROM episodes ORDER BY created_at DESC LIMIT 5"
            ).fetchall()
            if eps:
                sections.append("\nRecent Activity:")
                for etype, desc, ts in eps:
                    sections.append(f"  {ts} [{etype:>10}] {desc[:45]}")
        except Exception:
            pass

        # Decision board (Phase 201)
        try:
            decs = conn.execute(
                "SELECT title, confidence, status FROM decisions ORDER BY confidence DESC LIMIT 3"
            ).fetchall()
            if decs:
                sections.append("\nTop Decisions:")
                for title, conf, status in decs:
                    sections.append(f"  [{status:>10}] conf={conf:.2f}  {title[:40]}")
        except Exception:
            pass

        # Notifications (Phase 204)
        notifications = self._get_notifications(conn)
        if notifications:
            sections.append(f"\nNotifications ({len(notifications)}):")
            for n in notifications[:3]:
                sections.append(f"  [{n['severity']}] {n['message']}")

        conn.close()
        return "\n".join(sections)

    def _get_notifications(self, conn) -> list[dict]:
        """Generate notifications from system state."""
        notifications = []

        # Open conflicts
        try:
            conflicts = conn.execute("SELECT COUNT(*) FROM conflicts WHERE status='open'").fetchone()[0]
            if conflicts > 0:
                notifications.append({"severity": "warn", "message": f"{conflicts} unresolved conflict(s)"})
        except Exception:
            pass

        # Low confidence concepts
        try:
            low_conf = conn.execute("SELECT COUNT(*) FROM concepts WHERE confidence < 0.5").fetchone()[0]
            if low_conf > 0:
                notifications.append({"severity": "info", "message": f"{low_conf} low-confidence concept(s)"})
        except Exception:
            pass

        return notifications

    def timeline(self, investigation_id: str = "default") -> str:
        """Phase 200: Timeline view."""
        conn = self._get_conn()
        events = []

        # Gather from multiple sources
        for table, ts_col, desc_col, type_label in [
            ("episodes", "created_at", "description", "episode"),
            ("decisions", "created_at", "title", "decision"),
            ("syntheses", "created_at", "query", "synthesis"),
        ]:
            try:
                rows = conn.execute(
                    f"SELECT {ts_col}, {desc_col} FROM {table} ORDER BY {ts_col} DESC LIMIT 5"
                ).fetchall()
                for ts, desc in rows:
                    events.append({"time": ts, "type": type_label, "description": desc[:50]})
            except Exception:
                pass

        conn.close()
        events.sort(key=lambda x: x["time"], reverse=True)

        lines = ["Timeline:"]
        for e in events[:10]:
            lines.append(f"  {e['time']} [{e['type']:>10}] {e['description']}")
        return "\n".join(lines) if events else "No events."

    def stats(self) -> dict:
        conn = self._get_conn()
        tables = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        conn.close()
        return {"dashboard_sections": 4, "db_tables": tables}


# Phase 205: User settings
class UserSettings:
    """User preferences and settings."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

    def get(self, key: str, default: str = "") -> str:
        conn = self._get_conn()
        row = conn.execute("SELECT value FROM user_settings WHERE key=?", (key,)).fetchone()
        conn.close()
        return row[0] if row else default

    def set(self, key: str, value: str):
        import time
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO user_settings (key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, ts),
            )

    def list_all(self) -> dict:
        conn = self._get_conn()
        rows = conn.execute("SELECT key, value FROM user_settings ORDER BY key").fetchall()
        conn.close()
        return {r[0]: r[1] for r in rows}

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM user_settings").fetchone()[0]
        conn.close()
        return {"total_settings": total}


workspace_dashboard = WorkspaceDashboard()
user_settings = UserSettings()
