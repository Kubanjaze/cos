"""COS investigation UI — browse and manage investigations. Phase 196.

Text-based interface for investigation lifecycle management.
"""

import sqlite3
from typing import Optional
from cos.core.config import settings
from cos.core.logging import get_logger

logger = get_logger("cos.interface.investigation_ui")


class InvestigationUI:
    """Text-based investigation browser and manager."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or settings.db_path

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def dashboard(self, investigation_id: str = "default") -> str:
        """Generate a text dashboard for an investigation."""
        conn = self._get_conn()
        lines = []

        # Investigation header
        inv = conn.execute(
            "SELECT id, title, domain, status, created_at FROM investigations WHERE id=? OR id LIKE ?",
            (investigation_id, investigation_id + "%"),
        ).fetchone()
        if inv:
            lines.append(f"Investigation: {inv[1]}")
            lines.append(f"  ID: {inv[0]}  Domain: {inv[2] or '—'}  Status: {inv[3]}")
            lines.append(f"  Created: {inv[4]}")
        else:
            lines.append(f"Investigation: {investigation_id} (no record)")

        lines.append("")

        # Counts
        tables = [
            ("artifacts", "investigation_id"), ("documents", "investigation_id"),
            ("entities", "investigation_id"), ("concepts", "investigation_id"),
            ("episodes", "investigation_id"), ("decisions", "investigation_id"),
        ]
        lines.append("  Assets:")
        for table, col in tables:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {col}=?", (investigation_id,)).fetchone()[0]
                lines.append(f"    {table:>15}: {count}")
            except Exception:
                pass

        # Recent episodes
        try:
            eps = conn.execute(
                "SELECT episode_type, description, created_at FROM episodes WHERE investigation_id=? ORDER BY created_at DESC LIMIT 3",
                (investigation_id,),
            ).fetchall()
            if eps:
                lines.append("\n  Recent activity:")
                for etype, desc, ts in eps:
                    lines.append(f"    {ts} [{etype}] {desc[:50]}")
        except Exception:
            pass

        conn.close()
        return "\n".join(lines)

    def summary_all(self) -> str:
        """Summary of all investigations."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, title, domain, status, created_at FROM investigations ORDER BY created_at DESC"
        ).fetchall()
        conn.close()

        if not rows:
            return "No investigations."

        lines = [f"{'ID':>14} {'Status':>10} {'Domain':>12} {'Created':>20} Title"]
        for inv_id, title, domain, status, created in rows:
            lines.append(f"{inv_id:>14} {status:>10} {domain or '—':>12} {created:>20} {title[:35]}")
        return "\n".join(lines)

    def stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM investigations").fetchone()[0]
        by_status = conn.execute("SELECT status, COUNT(*) FROM investigations GROUP BY status").fetchall()
        conn.close()
        return {"total": total, "by_status": {s: c for s, c in by_status}}


investigation_ui = InvestigationUI()
