"""COS system health dashboard — cockpit view of all core modules.

Aggregates status from storage, cache, cost, tasks, investigations, rate limiters.

Usage:
    from cos.core.health import get_health_report
    report = get_health_report()
"""

from cos.core.logging import get_logger

logger = get_logger("cos.core.health")


def get_health_report() -> dict:
    """Aggregate health metrics from all COS core modules."""
    report = {"modules": {}}

    # Storage (Phase 108)
    try:
        from cos.core.storage import storage
        info = storage.info()
        report["storage"] = {
            "file_count": info["file_count"],
            "file_size_bytes": info["file_size_bytes"],
            "db_size_bytes": info["db_size_bytes"],
            "db_tables": info["db_tables"],
        }
        report["modules"]["storage"] = "ok"
    except Exception as e:
        report["modules"]["storage"] = f"error: {e}"

    # Cache (Phase 118)
    try:
        from cos.core.cache import cache_manager
        stats = cache_manager.stats()
        report["cache"] = stats
        report["modules"]["cache"] = "ok"
    except Exception as e:
        report["modules"]["cache"] = f"error: {e}"

    # Cost (Phase 104)
    try:
        from cos.core.cost import cost_tracker
        summary = cost_tracker.get_summary()
        report["cost"] = {
            "total_cost": summary["total_cost"],
            "total_events": summary["total_events"],
            "models": len(summary["by_model"]),
        }
        report["modules"]["cost"] = "ok"
    except Exception as e:
        report["modules"]["cost"] = f"error: {e}"

    # Tasks (Phase 107)
    try:
        from cos.core.tasks import task_queue
        tasks = task_queue.list_tasks(limit=1000)
        status_counts = {}
        for t in tasks:
            status_counts[t.status] = status_counts.get(t.status, 0) + 1
        report["tasks"] = status_counts
        report["modules"]["tasks"] = "ok"
    except Exception as e:
        report["modules"]["tasks"] = f"error: {e}"

    # Investigations (Phase 115)
    try:
        from cos.core.investigations import investigation_manager
        invs = investigation_manager.list_investigations()
        inv_counts = {}
        for i in invs:
            inv_counts[i["status"]] = inv_counts.get(i["status"], 0) + 1
        report["investigations"] = {"total": len(invs), "by_status": inv_counts}
        report["modules"]["investigations"] = "ok"
    except Exception as e:
        report["modules"]["investigations"] = f"error: {e}"

    # Rate limiters (Phase 119)
    try:
        from cos.core.ratelimit import all_stats
        rl_stats = all_stats()
        report["rate_limiters"] = {
            "active": len(rl_stats),
            "total_requests": sum(s["total_requests"] for s in rl_stats.values()),
            "total_waits": sum(s["total_waits"] for s in rl_stats.values()),
        }
        report["modules"]["ratelimit"] = "ok"
    except Exception as e:
        report["modules"]["ratelimit"] = f"error: {e}"

    # Config (Phase 102)
    try:
        from cos.core.config import settings
        errors = settings.validate()
        report["config"] = {"valid": len(errors) == 0, "errors": errors}
        report["modules"]["config"] = "ok"
    except Exception as e:
        report["modules"]["config"] = f"error: {e}"

    return report


def format_health_report(report: dict) -> str:
    """Format health report as human-readable string."""
    lines = [
        "COS System Health Report",
        "=" * 55,
        "",
    ]

    # Modules status
    lines.append("Modules:")
    for mod, status in sorted(report.get("modules", {}).items()):
        icon = "OK" if status == "ok" else "!!"
        lines.append(f"  [{icon}] {mod}")

    # Storage
    s = report.get("storage", {})
    if s:
        lines.append(f"\nStorage:")
        lines.append(f"  Files:    {s.get('file_count', 0)} ({s.get('file_size_bytes', 0):,} bytes)")
        lines.append(f"  Database: {s.get('db_size_bytes', 0):,} bytes ({len(s.get('db_tables', []))} tables)")

    # Cache
    c = report.get("cache", {})
    if c:
        lines.append(f"\nCache:")
        lines.append(f"  Active:   {c.get('active_entries', 0)} entries")
        lines.append(f"  Hits:     {c.get('total_hits', 0)}")

    # Cost
    co = report.get("cost", {})
    if co:
        lines.append(f"\nCost:")
        lines.append(f"  Total:    ${co.get('total_cost', 0):.4f} ({co.get('total_events', 0)} events)")

    # Tasks
    t = report.get("tasks", {})
    if t:
        lines.append(f"\nTasks:")
        for status, count in sorted(t.items()):
            lines.append(f"  {status:>12}: {count}")

    # Investigations
    inv = report.get("investigations", {})
    if inv:
        lines.append(f"\nInvestigations: {inv.get('total', 0)} total")
        for status, count in sorted(inv.get("by_status", {}).items()):
            lines.append(f"  {status:>12}: {count}")

    # Config
    cfg = report.get("config", {})
    if cfg:
        lines.append(f"\nConfig: {'Valid' if cfg.get('valid') else 'INVALID'}")

    return "\n".join(lines)
