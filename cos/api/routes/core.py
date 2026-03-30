"""COS API — Core routes (health, status, investigations, config)."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/dashboard")
def get_dashboard():
    """Full system dashboard data."""
    from cos.core.config import settings
    import sqlite3
    conn = sqlite3.connect(settings.db_path)

    counts = {}
    for table in ["investigations", "artifacts", "documents", "entities",
                   "concepts", "hypotheses", "decisions", "episodes",
                   "entity_relations", "provenance"]:
        try:
            counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except Exception:
            counts[table] = 0

    # Recent episodes
    recent = []
    try:
        rows = conn.execute(
            "SELECT episode_type, description, created_at FROM episodes ORDER BY created_at DESC LIMIT 5"
        ).fetchall()
        recent = [{"type": r[0], "description": r[1], "created_at": r[2]} for r in rows]
    except Exception:
        pass

    # Notifications
    notifications = []
    try:
        conflicts = conn.execute("SELECT COUNT(*) FROM conflicts WHERE status='open'").fetchone()[0]
        if conflicts > 0:
            notifications.append({"severity": "warn", "message": f"{conflicts} unresolved conflict(s)"})
        low_conf = conn.execute("SELECT COUNT(*) FROM concepts WHERE confidence < 0.5").fetchone()[0]
        if low_conf > 0:
            notifications.append({"severity": "info", "message": f"{low_conf} low-confidence concept(s)"})
    except Exception:
        pass

    conn.close()
    return {"counts": counts, "recent_activity": recent, "notifications": notifications}


@router.get("/health")
def get_health():
    """System health check."""
    from cos.core.health import get_health_report
    return get_health_report()


@router.get("/investigations")
def list_investigations():
    from cos.core.investigations import investigation_manager
    return investigation_manager.list_investigations()


@router.get("/investigations/{inv_id}")
def get_investigation(inv_id: str):
    from cos.core.investigations import investigation_manager
    return investigation_manager.get(inv_id)


@router.get("/cost")
def get_cost():
    from cos.core.cost import cost_tracker
    return cost_tracker.get_summary()
