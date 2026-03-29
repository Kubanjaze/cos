"""COS CLI entry point — run with `python -m cos`."""

import sys
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import argparse
import os
from pathlib import Path
from cos import __version__


def main():
    parser = argparse.ArgumentParser(
        prog="cos",
        description="COS — Cognitive Operating System",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"cos {__version__}")

    sub = parser.add_subparsers(dest="command", help="Available commands")
    sub.add_parser("status", help="Show system status")
    sub.add_parser("info", help="Show package info")

    config_parser = sub.add_parser("config", help="Configuration management")
    config_sub = config_parser.add_subparsers(dest="config_command")
    config_sub.add_parser("show", help="Show current configuration")
    config_sub.add_parser("validate", help="Validate configuration")

    sub.add_parser("events", help="List registered event types + listeners")

    batch_parser = sub.add_parser("batch", help="Batch operations")
    batch_sub = batch_parser.add_subparsers(dest="batch_command")
    batch_ingest_p = batch_sub.add_parser("ingest", help="Batch ingest files from directory")
    batch_ingest_p.add_argument("directory", help="Directory with files to ingest")
    batch_ingest_p.add_argument("--investigation", default="default")

    inv_parser = sub.add_parser("investigate", help="Investigation management")
    inv_sub = inv_parser.add_subparsers(dest="inv_command")
    inv_create_p = inv_sub.add_parser("create", help="Create investigation")
    inv_create_p.add_argument("title", help="Investigation question/title")
    inv_create_p.add_argument("--domain", default="")
    inv_create_p.add_argument("--tags", default="")
    inv_sub.add_parser("list", help="List investigations")
    inv_show_p = inv_sub.add_parser("show", help="Show investigation detail")
    inv_show_p.add_argument("inv_id", help="Investigation ID")
    inv_activate_p = inv_sub.add_parser("activate", help="Activate investigation")
    inv_activate_p.add_argument("inv_id")
    inv_complete_p = inv_sub.add_parser("complete", help="Complete investigation")
    inv_complete_p.add_argument("inv_id")

    sub.add_parser("plugins", help="List registered plugins")

    pipe_parser = sub.add_parser("pipeline", help="Pipeline management")
    pipe_sub = pipe_parser.add_subparsers(dest="pipeline_command")
    pipe_sub.add_parser("list", help="List pipelines")
    pipe_run_p = pipe_sub.add_parser("run", help="Run a pipeline")
    pipe_run_p.add_argument("pipeline_name", help="Pipeline name")
    pipe_run_p.add_argument("--investigation", default="default")

    ingest_parser = sub.add_parser("ingest", help="Ingest a file into COS")
    ingest_parser.add_argument("file", help="Path to file (PDF, CSV, TXT)")
    ingest_parser.add_argument("--investigation", default="default", help="Investigation ID")

    artifacts_parser = sub.add_parser("artifacts", help="List ingested artifacts")
    artifacts_parser.add_argument("--investigation", default=None, help="Filter by investigation")

    tag_parser = sub.add_parser("tag", help="Tag an artifact with metadata")
    tag_parser.add_argument("artifact_id", help="Artifact ID (full or partial)")
    tag_parser.add_argument("--domain", help="Domain (e.g., cheminformatics, clinical)")
    tag_parser.add_argument("--source", help="Data source")
    tag_parser.add_argument("--tags", help="Comma-separated tags")
    tag_parser.add_argument("--description", help="Description")

    search_parser = sub.add_parser("search", help="Search artifacts by metadata")
    search_parser.add_argument("--domain", help="Filter by domain")
    search_parser.add_argument("--tag", help="Filter by tag")
    search_parser.add_argument("--source", help="Filter by source")

    sub.add_parser("storage", help="Show storage backend info")

    version_parser = sub.add_parser("version", help="Version management")
    version_sub = version_parser.add_subparsers(dest="version_command")
    vlist_p = version_sub.add_parser("list", help="List versions for an investigation")
    vlist_p.add_argument("investigation_id", help="Investigation ID")

    task_parser = sub.add_parser("task", help="Task queue management")
    task_sub = task_parser.add_subparsers(dest="task_command")
    submit_p = task_sub.add_parser("submit", help="Submit a task")
    submit_p.add_argument("task_cmd", help="Command to run (e.g., 'cos info')")
    submit_p.add_argument("--investigation", default="default")
    task_sub.add_parser("list", help="List tasks")
    status_p = task_sub.add_parser("status", help="Get task status")
    status_p.add_argument("task_id", help="Task ID (full or partial)")
    task_sub.add_parser("run", help="Process pending tasks")

    sub.add_parser("health", help="System health dashboard")

    docs_parser = sub.add_parser("docs", help="Document store")
    docs_sub = docs_parser.add_subparsers(dest="docs_command")
    docs_sub.add_parser("list", help="List documents")
    docs_show_p = docs_sub.add_parser("show", help="Show document detail")
    docs_show_p.add_argument("doc_id")
    docs_store_p = docs_sub.add_parser("store", help="Store document from artifact")
    docs_store_p.add_argument("artifact_id")
    docs_store_p.add_argument("--investigation", default="default")
    docs_search_p = docs_sub.add_parser("search", help="Search document text")
    docs_search_p.add_argument("query")
    sub.add_parser("ratelimit", help="Rate limiter stats")

    cache_parser = sub.add_parser("cache", help="Cache management")
    cache_sub = cache_parser.add_subparsers(dest="cache_command")
    cache_sub.add_parser("stats", help="Show cache statistics")
    cache_sub.add_parser("clear", help="Clear all cache entries")

    cost_parser = sub.add_parser("cost", help="Cost tracking")
    cost_sub = cost_parser.add_subparsers(dest="cost_command")
    cost_sub.add_parser("summary", help="Show cost summary")
    cost_sub.add_parser("reset", help="Clear all cost events")

    args = parser.parse_args()

    if args.command == "ingest":
        from cos.core.ingestion import ingest_file
        try:
            artifact = ingest_file(args.file, investigation_id=args.investigation)
            print(f"Ingested: {artifact.uri}")
            print(f"  ID:     {artifact.id}")
            print(f"  Type:   {artifact.type}")
            print(f"  Hash:   {artifact.hash[:16]}...")
            print(f"  Size:   {artifact.size_bytes} bytes")
            print(f"  Stored: {artifact.stored_path}")
        except Exception as e:
            print(f"Error: {e}")

    elif args.command == "artifacts":
        from cos.core.ingestion import list_artifacts
        artifacts = list_artifacts(args.investigation)
        if not artifacts:
            print("No artifacts found.")
        else:
            print(f"{'ID':>8} {'Type':>4} {'Size':>8} {'Investigation':>15} {'Hash':>14} Created")
            for a in artifacts:
                print(f"{a['id'][:8]:>8} {a['type']:>4} {a['size_bytes']:>8} {a['investigation_id']:>15} {a['hash']:>14} {a['created_at']}")

    elif args.command == "tag":
        from cos.core.tagging import tag_artifact, get_tags
        try:
            tag_list = [t.strip() for t in args.tags.split(",")] if args.tags else None
            count = tag_artifact(args.artifact_id, domain=args.domain, source=args.source,
                                 tags=tag_list, description=args.description)
            print(f"Added {count} tags to artifact {args.artifact_id}")
            all_tags = get_tags(args.artifact_id)
            for key, vals in all_tags.items():
                print(f"  {key}: {', '.join(vals)}")
        except Exception as e:
            print(f"Error: {e}")

    elif args.command == "search":
        from cos.core.tagging import search_artifacts
        results = search_artifacts(domain=args.domain, tag=args.tag, source=args.source)
        if not results:
            print("No matching artifacts found.")
        else:
            print(f"Found {len(results)} artifact(s):\n")
            for a in results:
                print(f"  {a['id'][:8]}  {a['type']:>4}  {a['size_bytes']:>6}B  {a['investigation_id']:>12}  {a['created_at']}")
                for key, vals in a.get("tags", {}).items():
                    print(f"           {key}: {', '.join(vals)}")
                print()

    elif args.command == "batch":
        if args.batch_command == "ingest":
            from cos.core.batch import batch_executor
            from cos.core.ingestion import ingest_file, HANDLERS
            import glob
            # Find supported files
            files = []
            for ext in HANDLERS:
                files.extend(glob.glob(os.path.join(args.directory, f"*{ext}")))
            if not files:
                print(f"No supported files found in {args.directory}")
            else:
                result = batch_executor.run(
                    items=files,
                    operation=lambda f: ingest_file(f, investigation_id=args.investigation),
                    investigation_id=args.investigation,
                    description=f"Batch ingest from {args.directory}",
                )
                print(f"\nBatch: {result.description}")
                print(f"  Total: {result.total} | Succeeded: {result.succeeded} | Failed: {result.failed}")
                print(f"  Duration: {result.duration_s}s | Rate: {result.items_per_sec} items/s")
                if result.errors:
                    print(f"  Errors:")
                    for e in result.errors[:5]:
                        print(f"    [{e['index']}] {e['item'][:40]}: {e['error'][:60]}")
        else:
            batch_parser.print_help()

    elif args.command == "events":
        from cos.core.events import event_bus
        events = event_bus.list_events()
        print(f"COS Event Bus ({event_bus.total_listeners} listeners, {event_bus.total_emits} emits)")
        print("=" * 40)
        if not events:
            print("No event listeners registered.")
        else:
            for etype, count in events.items():
                print(f"  {etype:30s} {count} listener(s)")

    elif args.command == "investigate":
        from cos.core.investigations import investigation_manager
        if args.inv_command == "create":
            inv_id = investigation_manager.create(args.title, domain=args.domain, tags=args.tags)
            print(f"Investigation created: {inv_id}")
        elif args.inv_command == "list":
            invs = investigation_manager.list_investigations()
            if not invs:
                print("No investigations.")
            else:
                print(f"{'ID':>14} {'Status':>10} {'Domain':>15} {'Created':>20} Title")
                for i in invs:
                    print(f"{i['id']:>14} {i['status']:>10} {i['domain']:>15} {i['created_at']:>20} {i['title'][:40]}")
        elif args.inv_command == "show":
            detail = investigation_manager.get(args.inv_id)
            if not detail:
                print(f"Not found: {args.inv_id}")
            else:
                print(f"Investigation: {detail['id']}")
                print(f"  Title:      {detail['title']}")
                print(f"  Domain:     {detail['domain'] or '—'}")
                print(f"  Status:     {detail['status']}")
                print(f"  Created:    {detail['created_at']}")
                print(f"  Updated:    {detail['updated_at']}")
                print(f"  Tags:       {detail['tags'] or '—'}")
                print(f"  Artifacts:  {detail['artifacts']}")
                print(f"  Versions:   {detail['versions']}")
                print(f"  Cost:       ${detail['total_cost']:.4f}")
        elif args.inv_command == "activate":
            investigation_manager.activate(args.inv_id)
            print(f"Investigation {args.inv_id} activated.")
        elif args.inv_command == "complete":
            investigation_manager.complete(args.inv_id)
            print(f"Investigation {args.inv_id} completed.")
        else:
            inv_parser.print_help()

    elif args.command == "pipeline":
        from cos.core.pipelines import pipeline_registry
        if args.pipeline_command == "list":
            pipelines = pipeline_registry.list_pipelines()
            if not pipelines:
                print("No pipelines registered.")
            else:
                print(f"Registered pipelines:")
                for p in pipelines:
                    print(f"  {p['name']:20s} ({p['steps']} steps) — {p['description']}")
        elif args.pipeline_command == "run":
            import json
            result = pipeline_registry.run(args.pipeline_name, investigation_id=args.investigation)
            print(f"\nPipeline: {result['pipeline']} — {result['status']}")
            for step in result["steps"]:
                status = "OK" if step["status"] == "completed" else "FAIL"
                cmd = step["command"] + (f" {step.get('subcommand','')}" if step.get("subcommand") else "")
                print(f"  Step {step['step']}: {cmd:20s} [{status}] {step['duration_s']:.3f}s")
            if result.get("total_duration_s"):
                print(f"\nTotal: {result['total_duration_s']:.3f}s")
        else:
            pipe_parser.print_help()

    elif args.command == "plugins":
        from cos.core.plugins import plugin_registry
        plugins = plugin_registry.list_plugins()
        print(f"COS Plugins ({plugin_registry.total_count} total)")
        print("=" * 40)
        for ptype, names in plugins.items():
            print(f"\n{ptype} ({len(names)}):")
            for n in names:
                print(f"  {n}")

    elif args.command == "version":
        from cos.core.versioning import version_manager
        if args.version_command == "list":
            versions = version_manager.get_versions(args.investigation_id)
            if not versions:
                print(f"No versions for investigation '{args.investigation_id}'.")
            else:
                print(f"Versions for '{args.investigation_id}':")
                for v in versions:
                    art = v.artifact_id[:8] + "..." if v.artifact_id else "—"
                    print(f"  v{v.version_number}  {v.created_at}  artifact={art}  {v.description}")
        else:
            version_parser.print_help()

    elif args.command == "storage":
        from cos.core.storage import storage
        info = storage.info()
        print(f"COS Storage Info")
        print(f"{'='*45}")
        print(f"Files:")
        print(f"  Backend:  {info['file_backend']}")
        print(f"  Base dir: {info['file_base']}")
        print(f"  Files:    {info['file_count']}")
        print(f"  Size:     {info['file_size_bytes']:,} bytes")
        print(f"\nDatabase:")
        print(f"  Backend:  {info['db_backend']}")
        print(f"  Path:     {info['db_path']}")
        print(f"  Size:     {info['db_size_bytes']:,} bytes")
        print(f"  Tables:   {', '.join(info['db_tables'])}")

    elif args.command == "task":
        from cos.core.tasks import task_queue
        if args.task_command == "submit":
            tid = task_queue.submit(args.task_cmd, investigation_id=args.investigation)
            print(f"Task submitted: {tid[:8]}...")
        elif args.task_command == "list":
            tasks = task_queue.list_tasks()
            if not tasks:
                print("No tasks.")
            else:
                print(f"{'ID':>8} {'Status':>10} {'Investigation':>14} {'Submitted':>20} Command")
                for t in tasks:
                    print(f"{t.id[:8]:>8} {t.status:>10} {t.investigation_id:>14} {t.submitted_at:>20} {t.command[:40]}")
        elif args.task_command == "status":
            t = task_queue.get_status(args.task_id)
            if not t:
                print(f"Task not found: {args.task_id}")
            else:
                print(f"Task: {t.id}")
                print(f"Status: {t.status}")
                print(f"Command: {t.command}")
                print(f"Investigation: {t.investigation_id}")
                print(f"Submitted: {t.submitted_at}")
                print(f"Started: {t.started_at or '—'}")
                print(f"Completed: {t.completed_at or '—'}")
                if t.error:
                    print(f"Error: {t.error[:200]}")
                if t.result_path and os.path.exists(t.result_path):
                    print(f"\nResult:\n{Path(t.result_path).read_text(encoding='utf-8')[:500]}")
        elif args.task_command == "run":
            n = task_queue.run_worker()
            print(f"Processed {n} tasks.")
        else:
            task_parser.print_help()

    elif args.command == "docs":
        from cos.memory.documents import document_store
        if args.docs_command == "list":
            docs = document_store.list_documents()
            if not docs:
                print("No documents stored.")
            else:
                print(f"{'ID':>12} {'Title':>15} {'Chunks':>6} {'Chars':>8} {'Investigation':>14} Created")
                for d in docs:
                    print(f"{d.id:>12} {d.title[:15]:>15} {d.chunk_count:>6} {d.char_count:>8} {d.investigation_id:>14} {d.created_at}")
        elif args.docs_command == "show":
            doc = document_store.get_document(args.doc_id)
            if not doc:
                print(f"Not found: {args.doc_id}")
            else:
                print(f"Document: {doc.id}")
                print(f"  Title:    {doc.title}")
                print(f"  Artifact: {doc.artifact_id[:12]}...")
                print(f"  Chars:    {doc.char_count}")
                print(f"  Chunks:   {doc.chunk_count}")
                chunks = document_store.get_chunks(doc.id)
                print(f"\nChunks:")
                for c in chunks[:5]:
                    print(f"  [{c.chunk_index}] ({c.char_count} chars) {c.chunk_text[:80]}...")
        elif args.docs_command == "store":
            doc_id = document_store.store_document(args.artifact_id, investigation_id=args.investigation)
            doc = document_store.get_document(doc_id)
            print(f"Document stored: {doc_id} ({doc.chunk_count} chunks, {doc.char_count} chars)")
        elif args.docs_command == "search":
            results = document_store.search_text(args.query)
            if not results:
                print(f"No results for '{args.query}'")
            else:
                print(f"Found {len(results)} result(s) for '{args.query}':")
                for r in results:
                    print(f"  [{r['doc_id']}:{r['chunk_index']}] {r['title']} — {r['text'][:80]}...")
        else:
            docs_parser.print_help()

    elif args.command == "health":
        from cos.core.health import get_health_report, format_health_report
        report = get_health_report()
        print(format_health_report(report))

    elif args.command == "ratelimit":
        from cos.core.ratelimit import all_stats
        stats = all_stats()
        if not stats:
            print("No rate limiters active.")
        else:
            print(f"COS Rate Limiters ({len(stats)} active)")
            print("=" * 50)
            for name, s in stats.items():
                print(f"  {name:20s} rate={s['rate']}/s cap={s['capacity']} "
                      f"reqs={s['total_requests']} waits={s['total_waits']} "
                      f"wait_time={s['total_wait_time_s']:.3f}s")

    elif args.command == "cache":
        from cos.core.cache import cache_manager
        if args.cache_command == "stats":
            s = cache_manager.stats()
            print(f"COS Cache Stats")
            print(f"  Active entries: {s['active_entries']}")
            print(f"  Expired entries: {s['expired_entries']}")
            print(f"  Total hits: {s['total_hits']}")
        elif args.cache_command == "clear":
            n = cache_manager.clear()
            print(f"Cache cleared: {n} entries removed.")
        else:
            cache_parser.print_help()

    elif args.command == "cost":
        from cos.core.cost import cost_tracker
        if args.cost_command == "summary":
            s = cost_tracker.get_summary()
            print(f"COS Cost Summary")
            print(f"{'='*45}")
            print(f"Total cost:   ${s['total_cost']:.4f}")
            print(f"Total events: {s['total_events']}")
            if s["by_model"]:
                print(f"\nBy model:")
                for m in s["by_model"]:
                    print(f"  {m['model']:35s} {m['events']:3d} calls  ${m['cost']:.4f}")
            if s["by_investigation"]:
                print(f"\nBy investigation:")
                for inv in s["by_investigation"]:
                    print(f"  {inv['investigation_id']:35s} {inv['events']:3d} calls  ${inv['cost']:.4f}")
        elif args.cost_command == "reset":
            cost_tracker.reset()
            print("Cost events cleared.")
        else:
            cost_parser.print_help()

    elif args.command == "config":
        from cos.core.config import settings
        if args.config_command == "show":
            print(settings.show())
        elif args.config_command == "validate":
            errors = settings.validate()
            if errors:
                print("Configuration errors:")
                for e in errors:
                    print(f"  - {e}")
            else:
                print("Configuration valid.")
        else:
            config_parser.print_help()

    elif args.command == "status":
        print(f"COS v{__version__}")
        print("Packages:")
        for pkg in ["core", "memory", "reasoning", "workflow", "decision", "interface", "intelligence", "autonomy"]:
            try:
                mod = __import__(f"cos.{pkg}", fromlist=[pkg])
                print(f"  cos.{pkg}: v{mod.__version__}")
            except ImportError as e:
                print(f"  cos.{pkg}: MISSING ({e})")

    elif args.command == "info":
        print(f"COS — Cognitive Operating System v{__version__}")
        print("Tracks: A (Core), B (Memory), C (Reasoning), D (Workflow),")
        print("        E (Decision), F (Interface), G (Intelligence), H (Autonomy)")
        print("Build: Monorepo with service directories (ADR-004)")
        print("Storage: SQLite + filesystem (ADR-002)")
        print("Unit of work: Investigation (ADR-003)")

    elif args.command is None:
        parser.print_help()


if __name__ == "__main__":
    main()
