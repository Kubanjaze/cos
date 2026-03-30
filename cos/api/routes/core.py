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

    # Notifications (with links to detail pages)
    notifications = []
    try:
        conflicts = conn.execute("SELECT COUNT(*) FROM conflicts WHERE status='open'").fetchone()[0]
        if conflicts > 0:
            notifications.append({"severity": "warn", "message": f"{conflicts} unresolved conflict(s)", "link": "conflicts"})
        low_conf = conn.execute("SELECT COUNT(*) FROM concepts WHERE confidence < 0.5").fetchone()[0]
        if low_conf > 0:
            notifications.append({"severity": "info", "message": f"{low_conf} low-confidence concept(s)", "link": "low-confidence"})
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


@router.get("/artifacts")
def list_artifacts():
    from cos.core.ingestion import list_artifacts
    return list_artifacts(None)


@router.get("/episodes")
def list_episodes():
    from cos.memory.episodic import episodic_memory
    eps = episodic_memory.recall(limit=50)
    return [{"id": e.id, "type": e.episode_type, "description": e.description,
             "investigation_id": e.investigation_id, "duration_s": e.duration_s,
             "cost_usd": e.cost_usd, "created_at": e.created_at} for e in eps]


@router.get("/documents")
def list_documents():
    from cos.memory.documents import document_store
    docs = document_store.list_documents()
    return [{"id": d.id, "title": d.title, "artifact_id": d.artifact_id,
             "chunks": d.chunk_count, "chars": d.char_count,
             "investigation_id": d.investigation_id, "created_at": d.created_at} for d in docs]


@router.get("/provenance/stats")
def provenance_stats():
    from cos.memory.provenance import provenance_tracker
    return provenance_tracker.stats()


@router.post("/ingest/path")
def ingest_by_path(file_path: str = "", investigation_id: str = "default"):
    """Ingest a local file by path."""
    from cos.core.ingestion import ingest_file
    try:
        artifact = ingest_file(file_path, investigation_id=investigation_id)
        return {"status": "success", "id": artifact.id, "uri": artifact.uri,
                "type": artifact.type, "size": artifact.size_bytes, "hash": artifact.hash[:16]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/conflicts")
def list_conflicts():
    from cos.memory.conflicts import conflict_detector
    conflicts = conflict_detector.list_conflicts()
    return [{"id": c.id, "type": c.conflict_type, "description": c.description,
             "severity": c.severity, "status": c.status, "resolution": c.resolution,
             "item_a": f"{c.item_a_type}/{c.item_a_id}", "item_b": f"{c.item_b_type}/{c.item_b_id}",
             "created_at": c.created_at} for c in conflicts]


@router.get("/low-confidence")
def low_confidence_concepts():
    from cos.core.config import settings
    import sqlite3
    conn = sqlite3.connect(settings.db_path)
    rows = conn.execute(
        "SELECT id, name, definition, domain, confidence FROM concepts WHERE confidence < 0.5 ORDER BY confidence"
    ).fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "definition": r[2], "domain": r[3], "confidence": r[4]} for r in rows]


@router.get("/provenance/recent")
def provenance_recent():
    from cos.core.config import settings
    import sqlite3
    conn = sqlite3.connect(settings.db_path)
    rows = conn.execute(
        "SELECT target_type, target_id, source_type, source_id, operation, agent, created_at "
        "FROM provenance ORDER BY created_at DESC LIMIT 30"
    ).fetchall()
    conn.close()
    return [{"target_type": r[0], "target_id": r[1], "source_type": r[2],
             "source_id": r[3], "operation": r[4], "agent": r[5], "created_at": r[6]} for r in rows]
