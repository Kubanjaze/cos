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

    ep_parser = sub.add_parser("episodes", help="Episodic memory")
    ep_sub = ep_parser.add_subparsers(dest="ep_command")
    ep_list_p = ep_sub.add_parser("list", help="List episodes")
    ep_list_p.add_argument("--investigation", default=None)
    ep_list_p.add_argument("--type", default=None)
    ep_record_p = ep_sub.add_parser("record", help="Record an episode")
    ep_record_p.add_argument("description")
    ep_record_p.add_argument("--type", default="manual")
    ep_record_p.add_argument("--investigation", default="default")
    ep_sub.add_parser("stats", help="Episode statistics")

    temp_parser = sub.add_parser("temporal", help="Temporal tagging")
    temp_sub = temp_parser.add_subparsers(dest="temp_command")
    temp_tag_p = temp_sub.add_parser("tag", help="Add temporal tag")
    temp_tag_p.add_argument("target_type", help="entity, document, or relation")
    temp_tag_p.add_argument("target_id")
    temp_tag_p.add_argument("--context", required=True, help="Time context description")
    temp_tag_p.add_argument("--time-point", default=None)
    temp_tag_p.add_argument("--investigation", default="default")
    temp_timeline_p = temp_sub.add_parser("timeline", help="Show investigation timeline")
    temp_timeline_p.add_argument("investigation_id")

    rel_parser = sub.add_parser("relations", help="Relationship extraction")
    rel_sub = rel_parser.add_subparsers(dest="rel_command")
    rel_extract_p = rel_sub.add_parser("extract", help="Extract relations from document")
    rel_extract_p.add_argument("doc_id")
    rel_list_p = rel_sub.add_parser("list", help="List relations")
    rel_list_p.add_argument("--entity", default=None)
    rel_list_p.add_argument("--type", default=None)
    rel_sub.add_parser("stats", help="Relation statistics")

    ent_parser = sub.add_parser("entities", help="Entity extraction")
    ent_sub = ent_parser.add_subparsers(dest="ent_command")
    ent_extract_p = ent_sub.add_parser("extract", help="Extract entities from document")
    ent_extract_p.add_argument("doc_id")
    ent_list_p = ent_sub.add_parser("list", help="List entities")
    ent_list_p.add_argument("--type", default=None, help="Filter by entity type")
    ent_sub.add_parser("stats", help="Entity statistics")

    embed_parser = sub.add_parser("embed", help="Embedding pipeline")
    embed_sub = embed_parser.add_subparsers(dest="embed_command")
    embed_doc_p = embed_sub.add_parser("doc", help="Embed a document's chunks")
    embed_doc_p.add_argument("doc_id")
    embed_search_p = embed_sub.add_parser("search", help="Semantic search")
    embed_search_p.add_argument("query")
    embed_search_p.add_argument("--top-k", type=int, default=5)
    embed_sub.add_parser("stats", help="Embedding statistics")

    concept_parser = sub.add_parser("concepts", help="Semantic memory (concepts)")
    concept_sub = concept_parser.add_subparsers(dest="concept_command")
    concept_def_p = concept_sub.add_parser("define", help="Define a concept")
    concept_def_p.add_argument("name", help="Concept name")
    concept_def_p.add_argument("definition", help="Concept definition")
    concept_def_p.add_argument("--domain", default="general", help="Domain (e.g., cheminformatics)")
    concept_def_p.add_argument("--category", default="general", help="Category (e.g., target, compound)")
    concept_def_p.add_argument("--confidence", type=float, default=0.5, help="Confidence 0-1")
    concept_def_p.add_argument("--source", default="", help="Source reference")
    concept_def_p.add_argument("--investigation", default="default")
    concept_list_p = concept_sub.add_parser("list", help="List concepts")
    concept_list_p.add_argument("--domain", default=None)
    concept_list_p.add_argument("--category", default=None)
    concept_get_p = concept_sub.add_parser("get", help="Get concept by name")
    concept_get_p.add_argument("name")
    concept_get_p.add_argument("--domain", default=None)
    concept_search_p = concept_sub.add_parser("search", help="Search concepts")
    concept_search_p.add_argument("query", help="Text to search in name/definition")
    concept_search_p.add_argument("--domain", default=None)
    concept_search_p.add_argument("--category", default=None)
    concept_update_p = concept_sub.add_parser("update", help="Update a concept")
    concept_update_p.add_argument("name")
    concept_update_p.add_argument("--domain", default="general")
    concept_update_p.add_argument("--definition", default=None)
    concept_update_p.add_argument("--confidence", type=float, default=None)
    concept_update_p.add_argument("--category", default=None)
    concept_sub.add_parser("stats", help="Concept statistics")

    proc_parser = sub.add_parser("procedures", help="Procedural memory (saved workflows)")
    proc_sub = proc_parser.add_subparsers(dest="proc_command")
    proc_def_p = proc_sub.add_parser("define", help="Define a procedure")
    proc_def_p.add_argument("name", help="Procedure name")
    proc_def_p.add_argument("steps_json", help='Steps as JSON array, e.g. \'[{"command":"status"}]\'')
    proc_def_p.add_argument("--description", default="", help="Procedure description")
    proc_def_p.add_argument("--domain", default="general")
    proc_def_p.add_argument("--category", default="general")
    proc_def_p.add_argument("--source", default="", help="Source reference")
    proc_def_p.add_argument("--investigation", default="default")
    proc_list_p = proc_sub.add_parser("list", help="List procedures")
    proc_list_p.add_argument("--domain", default=None)
    proc_list_p.add_argument("--category", default=None)
    proc_get_p = proc_sub.add_parser("get", help="Get procedure by name")
    proc_get_p.add_argument("name")
    proc_run_p = proc_sub.add_parser("run", help="Run a procedure")
    proc_run_p.add_argument("name")
    proc_run_p.add_argument("--investigation", default="default")
    proc_update_p = proc_sub.add_parser("update", help="Update a procedure")
    proc_update_p.add_argument("name")
    proc_update_p.add_argument("--description", default=None)
    proc_update_p.add_argument("--steps-json", default=None, help="New steps JSON")
    proc_update_p.add_argument("--domain", default=None)
    proc_update_p.add_argument("--category", default=None)
    proc_del_p = proc_sub.add_parser("delete", help="Delete a procedure")
    proc_del_p.add_argument("name")
    proc_sub.add_parser("stats", help="Procedure statistics")

    graph_parser = sub.add_parser("graph", help="Knowledge graph queries")
    graph_sub = graph_parser.add_subparsers(dest="graph_command")
    graph_nb_p = graph_sub.add_parser("neighbors", help="Find neighbors of an entity")
    graph_nb_p.add_argument("entity", help="Entity name")
    graph_nb_p.add_argument("--relation", default=None, help="Filter by relation type")
    graph_path_p = graph_sub.add_parser("path", help="Find shortest path between entities")
    graph_path_p.add_argument("source", help="Source entity")
    graph_path_p.add_argument("target", help="Target entity")
    graph_path_p.add_argument("--max-depth", type=int, default=5)
    graph_sg_p = graph_sub.add_parser("subgraph", help="Extract neighborhood subgraph")
    graph_sg_p.add_argument("entity", help="Center entity")
    graph_sg_p.add_argument("--depth", type=int, default=2)
    graph_query_p = graph_sub.add_parser("query", help="Query graph with filters")
    graph_query_p.add_argument("--entity-type", default=None)
    graph_query_p.add_argument("--relation", default=None)
    graph_query_p.add_argument("--target", default=None)
    graph_sub.add_parser("stats", help="Graph statistics")

    prov_parser = sub.add_parser("provenance", help="Provenance tracking")
    prov_sub = prov_parser.add_subparsers(dest="prov_command")
    prov_trace_p = prov_sub.add_parser("trace", help="Trace sources of an output")
    prov_trace_p.add_argument("target_type", help="Type (entity, relation, chunk, document)")
    prov_trace_p.add_argument("target_id", help="Target ID")
    prov_chain_p = prov_sub.add_parser("chain", help="Find outputs derived from a source")
    prov_chain_p.add_argument("source_type", help="Type (artifact, document, chunk)")
    prov_chain_p.add_argument("source_id", help="Source ID")
    prov_lineage_p = prov_sub.add_parser("lineage", help="Full lineage to root")
    prov_lineage_p.add_argument("target_type")
    prov_lineage_p.add_argument("target_id")
    prov_reg_p = prov_sub.add_parser("register", help="Register a provenance link")
    prov_reg_p.add_argument("target_type")
    prov_reg_p.add_argument("target_id")
    prov_reg_p.add_argument("source_type")
    prov_reg_p.add_argument("source_id")
    prov_reg_p.add_argument("--operation", required=True)
    prov_reg_p.add_argument("--agent", default="")
    prov_reg_p.add_argument("--investigation", default="default")
    prov_sub.add_parser("backfill", help="Reconstruct provenance from existing data")
    prov_sub.add_parser("stats", help="Provenance statistics")

    conf_parser = sub.add_parser("conflicts", help="Conflict detection")
    conf_sub = conf_parser.add_subparsers(dest="conf_command")
    conf_sub.add_parser("scan", help="Scan for conflicts")
    conf_list_p = conf_sub.add_parser("list", help="List conflicts")
    conf_list_p.add_argument("--status", default=None)
    conf_list_p.add_argument("--type", default=None)
    conf_list_p.add_argument("--severity", default=None)
    conf_res_p = conf_sub.add_parser("resolve", help="Resolve a conflict")
    conf_res_p.add_argument("conflict_id")
    conf_res_p.add_argument("resolution")
    conf_sub.add_parser("stats", help="Conflict statistics")

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

    elif args.command == "episodes":
        from cos.memory.episodic import episodic_memory
        if args.ep_command == "list":
            eps = episodic_memory.recall(investigation_id=args.investigation, episode_type=args.type)
            if not eps:
                print("No episodes found.")
            else:
                for e in eps:
                    cost_str = f" ${e.cost_usd:.4f}" if e.cost_usd > 0 else ""
                    print(f"  {e.created_at}  [{e.episode_type:>10}] {e.description[:50]}{cost_str}")
        elif args.ep_command == "record":
            ep_id = episodic_memory.record(args.type, args.description, investigation_id=args.investigation)
            print(f"Episode recorded: {ep_id}")
        elif args.ep_command == "stats":
            s = episodic_memory.stats()
            print(f"Episodes: {s['total']} total, ${s['total_cost']:.4f} cost")
            for t, c in s["by_type"].items():
                print(f"  {t}: {c}")
        else:
            ep_parser.print_help()

    elif args.command == "temporal":
        from cos.memory.temporal import temporal_tagger
        if args.temp_command == "tag":
            tid = temporal_tagger.tag(args.target_type, args.target_id, args.context,
                                       time_point=args.time_point, investigation_id=args.investigation)
            print(f"Temporal tag created: {tid}")
        elif args.temp_command == "timeline":
            events = temporal_tagger.get_timeline(args.investigation_id)
            if not events:
                print(f"No temporal events for '{args.investigation_id}'")
            else:
                print(f"Timeline for '{args.investigation_id}' ({len(events)} events):\n")
                for e in events:
                    tp = e["time_point"] or e["created_at"]
                    print(f"  {tp}  [{e['target_type']}] {e['target_id'][:16]} — {e['time_context']}")
        else:
            temp_parser.print_help()

    elif args.command == "relations":
        from cos.memory.relations import relation_extractor
        if args.rel_command == "extract":
            n = relation_extractor.extract_from_document(args.doc_id)
            print(f"Extracted {n} relations from {args.doc_id}")
        elif args.rel_command == "list":
            rels = relation_extractor.get_relations(entity_name=args.entity, relation_type=args.type)
            if not rels:
                print("No relations found.")
            else:
                print(f"{'Source':>20} {'Relation':>22} {'Target':>15}")
                for r in rels[:20]:
                    print(f"{r.source_entity:>20} {r.relation_type:>22} {r.target_value:>15}")
        elif args.rel_command == "stats":
            s = relation_extractor.stats()
            print(f"Relations: {s['total']} total")
            for t, c in s["by_type"].items():
                print(f"  {t}: {c}")
        else:
            rel_parser.print_help()

    elif args.command == "entities":
        from cos.memory.entities import entity_extractor
        if args.ent_command == "extract":
            n = entity_extractor.extract_from_document(args.doc_id)
            print(f"Extracted {n} entities from {args.doc_id}")
        elif args.ent_command == "list":
            ents = entity_extractor.get_entities(entity_type=args.type)
            if not ents:
                print("No entities found.")
            else:
                print(f"{'Type':>15} {'Name':>20} {'Confidence':>10} Document")
                for e in ents:
                    print(f"{e.entity_type:>15} {e.name:>20} {e.confidence:>10.2f} {e.document_id[:12]}")
        elif args.ent_command == "stats":
            s = entity_extractor.stats()
            print(f"Entities: {s['total']} total")
            for t, c in s["by_type"].items():
                print(f"  {t}: {c}")
        else:
            ent_parser.print_help()

    elif args.command == "embed":
        from cos.memory.embeddings import embedding_pipeline
        if args.embed_command == "doc":
            n = embedding_pipeline.embed_document(args.doc_id)
            print(f"Embedded {n} chunks for document {args.doc_id}")
        elif args.embed_command == "search":
            results = embedding_pipeline.search(args.query, top_k=args.top_k)
            if not results:
                print("No results.")
            else:
                print(f"Semantic search: '{args.query}' (top {len(results)})\n")
                for i, r in enumerate(results, 1):
                    print(f"  {i}. [sim={r['similarity']:.4f}] {r['document_id'][:12]}")
                    print(f"     {r['text'][:100]}...")
                    print()
        elif args.embed_command == "stats":
            s = embedding_pipeline.stats()
            print(f"Embeddings: {s['total_embeddings']} chunks across {s['documents_embedded']} documents")
            print(f"Model: {s['model']}")
        else:
            embed_parser.print_help()

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

    elif args.command == "concepts":
        from cos.memory.semantic import semantic_memory
        if args.concept_command == "define":
            cid = semantic_memory.define(
                args.name, args.definition, domain=args.domain, category=args.category,
                confidence=args.confidence, source_ref=args.source,
                investigation_id=args.investigation,
            )
            print(f"Concept defined: {cid} — {args.name} (domain={args.domain})")
        elif args.concept_command == "list":
            concepts = semantic_memory.list_concepts(domain=args.domain, category=args.category)
            if not concepts:
                print("No concepts found.")
            else:
                print(f"{'Name':>20} {'Domain':>15} {'Category':>12} {'Conf':>5} {'Updated':>20}")
                for c in concepts:
                    print(f"{c.name:>20} {c.domain:>15} {c.category:>12} {c.confidence:>5.2f} {c.updated_at:>20}")
        elif args.concept_command == "get":
            c = semantic_memory.get(args.name, domain=args.domain)
            if not c:
                print(f"Concept not found: {args.name}")
            else:
                print(f"Concept: {c.name}")
                print(f"  ID:         {c.id}")
                print(f"  Domain:     {c.domain}")
                print(f"  Category:   {c.category}")
                print(f"  Confidence: {c.confidence:.2f}")
                print(f"  Source:     {c.source_ref or '—'}")
                print(f"  Inv:        {c.investigation_id}")
                print(f"  Created:    {c.created_at}")
                print(f"  Updated:    {c.updated_at}")
                print(f"\n  Definition: {c.definition}")
        elif args.concept_command == "search":
            results = semantic_memory.search(text=args.query, domain=args.domain, category=args.category)
            if not results:
                print(f"No concepts matching '{args.query}'")
            else:
                print(f"Found {len(results)} concept(s) matching '{args.query}':\n")
                for c in results:
                    print(f"  {c.name:>20} ({c.domain}/{c.category}) conf={c.confidence:.2f}")
                    print(f"  {'':>20} {c.definition[:80]}")
                    print()
        elif args.concept_command == "update":
            ok = semantic_memory.update(
                args.name, domain=args.domain, definition=args.definition,
                confidence=args.confidence, category=args.category,
            )
            if ok:
                print(f"Concept updated: {args.name} (domain={args.domain})")
            else:
                print(f"Concept not found: {args.name} (domain={args.domain})")
        elif args.concept_command == "stats":
            s = semantic_memory.stats()
            print(f"Semantic Memory: {s['total']} concepts, avg confidence={s['avg_confidence']:.3f}")
            if s["by_domain"]:
                print(f"\nBy domain:")
                for d, cnt in s["by_domain"].items():
                    print(f"  {d}: {cnt}")
            if s["by_category"]:
                print(f"\nBy category:")
                for cat, cnt in s["by_category"].items():
                    print(f"  {cat}: {cnt}")
        else:
            concept_parser.print_help()

    elif args.command == "procedures":
        from cos.memory.procedural import procedural_memory
        if args.proc_command == "define":
            try:
                import json as _json
                steps = _json.loads(args.steps_json)
                pid = procedural_memory.define(
                    args.name, steps, description=args.description, domain=args.domain,
                    category=args.category, source_ref=args.source,
                    investigation_id=args.investigation,
                )
                print(f"Procedure defined: {pid} — {args.name} ({len(steps)} steps)")
            except (ValueError, _json.JSONDecodeError) as e:
                print(f"Error: {e}")
        elif args.proc_command == "list":
            procs = procedural_memory.list_procedures(domain=args.domain, category=args.category)
            if not procs:
                print("No procedures found.")
            else:
                print(f"{'Name':>20} {'Domain':>10} {'Cat':>10} {'Runs':>5} {'OK':>4} {'Fail':>4} {'Last Status':>12}")
                for p in procs:
                    print(f"{p.name:>20} {p.domain:>10} {p.category:>10} "
                          f"{p.total_runs:>5} {p.success_count:>4} {p.fail_count:>4} "
                          f"{p.last_run_status or '—':>12}")
        elif args.proc_command == "get":
            p = procedural_memory.get(args.name)
            if not p:
                print(f"Procedure not found: {args.name}")
            else:
                print(f"Procedure: {p.name}")
                print(f"  ID:          {p.id}")
                print(f"  Domain:      {p.domain}")
                print(f"  Category:    {p.category}")
                print(f"  Description: {p.description or '—'}")
                print(f"  Steps:       {len(p.steps)}")
                print(f"  Schema ver:  {p.steps_schema_version}")
                print(f"  Runs:        {p.total_runs} (ok={p.success_count}, fail={p.fail_count})")
                print(f"  Success rate:{p.success_rate:.0%}" if p.total_runs > 0 else "  Success rate: —")
                print(f"  Last run:    {p.last_run_at or '—'} ({p.last_run_status or '—'})")
                print(f"  Source:      {p.source_ref or '—'}")
                print(f"  Inv:         {p.investigation_id}")
                print(f"  Created:     {p.created_at}")
                print(f"  Updated:     {p.updated_at}")
                print(f"\n  Steps:")
                for i, s in enumerate(p.steps, 1):
                    cmd = s["command"] + (f" {s['subcommand']}" if s.get("subcommand") else "")
                    kw = s.get("kwargs", {})
                    kw_str = f" {kw}" if kw else ""
                    print(f"    {i}. {cmd}{kw_str}")
        elif args.proc_command == "run":
            try:
                result = procedural_memory.run(args.name, investigation_id=args.investigation)
                print(f"\nProcedure: {result['procedure']} — {result['status']}")
                for step in result["steps"]:
                    status = "OK" if step["status"] == "completed" else "FAIL"
                    cmd = step["command"] + (f" {step.get('subcommand','')}" if step.get("subcommand") else "")
                    print(f"  Step {step['step']}: {cmd:25s} [{status}] {step['duration_s']:.3f}s")
                if result.get("total_duration_s"):
                    print(f"\nTotal: {result['total_duration_s']:.3f}s")
            except ValueError as e:
                print(f"Error: {e}")
        elif args.proc_command == "update":
            try:
                new_steps = None
                if args.steps_json:
                    import json as _json
                    new_steps = _json.loads(args.steps_json)
                ok = procedural_memory.update(
                    args.name, description=args.description, steps=new_steps,
                    domain=args.domain, category=args.category,
                )
                if ok:
                    print(f"Procedure updated: {args.name}")
                else:
                    print(f"Procedure not found: {args.name}")
            except (ValueError, Exception) as e:
                print(f"Error: {e}")
        elif args.proc_command == "delete":
            ok = procedural_memory.delete(args.name)
            if ok:
                print(f"Procedure deleted: {args.name}")
            else:
                print(f"Procedure not found: {args.name}")
        elif args.proc_command == "stats":
            s = procedural_memory.stats()
            print(f"Procedural Memory: {s['total']} procedures")
            print(f"  Total runs: {s['total_runs']} (ok={s['total_success']}, fail={s['total_fail']})")
            print(f"  Success rate: {s['success_rate']:.0%}" if s['total_runs'] > 0 else "  Success rate: —")
            if s["by_domain"]:
                print(f"\nBy domain:")
                for d, cnt in s["by_domain"].items():
                    print(f"  {d}: {cnt}")
            if s["by_category"]:
                print(f"\nBy category:")
                for cat, cnt in s["by_category"].items():
                    print(f"  {cat}: {cnt}")
        else:
            proc_parser.print_help()

    elif args.command == "graph":
        from cos.memory.graph import knowledge_graph
        if args.graph_command == "neighbors":
            results = knowledge_graph.neighbors(args.entity, relation_type=args.relation)
            if not results:
                print(f"No neighbors found for '{args.entity}'")
            else:
                print(f"Neighbors of '{args.entity}' ({len(results)}):\n")
                for r in results:
                    print(f"  {r['direction']:>8} —[{r['relation']}]→ {r['entity']} (conf={r['confidence']:.2f})")
        elif args.graph_command == "path":
            path = knowledge_graph.path(args.source, args.target, max_depth=args.max_depth)
            if path is None:
                print(f"No path found: {args.source} → {args.target} (max depth={args.max_depth})")
            else:
                print(f"Path ({len(path)} hops): {args.source} → {args.target}\n")
                for i, step in enumerate(path, 1):
                    print(f"  {i}. {step['from']} —[{step['relation']}]→ {step['to']}")
        elif args.graph_command == "subgraph":
            sub_g = knowledge_graph.subgraph(args.entity, depth=args.depth)
            print(f"Subgraph: center='{sub_g['center']}', depth={sub_g['depth']}")
            print(f"  Nodes: {sub_g['node_count']}")
            print(f"  Edges: {sub_g['edge_count']}")
            if sub_g['nodes']:
                print(f"\n  Nodes:")
                for n in sub_g['nodes'][:20]:
                    print(f"    {n}")
            if sub_g['edges']:
                print(f"\n  Edges:")
                for e in sub_g['edges'][:20]:
                    print(f"    {e['source']} —[{e['relation']}]→ {e['target']}")
        elif args.graph_command == "query":
            results = knowledge_graph.query(
                entity_type=args.entity_type, relation_type=args.relation,
                target=args.target,
            )
            if not results:
                print("No results.")
            else:
                print(f"Graph query results ({len(results)}):\n")
                for r in results:
                    print(f"  {r['source']:>20} —[{r['relation']}]→ {r['target']}")
        elif args.graph_command == "stats":
            s = knowledge_graph.stats()
            print(f"Knowledge Graph Statistics")
            print(f"  Nodes:              {s['nodes']}")
            print(f"  Edges:              {s['edges']}")
            print(f"  Avg degree:         {s['avg_degree']}")
            print(f"  Components:         {s['components']}")
            print(f"  Largest component:  {s['largest_component']} nodes")
        else:
            graph_parser.print_help()

    elif args.command == "provenance":
        from cos.memory.provenance import provenance_tracker
        if args.prov_command == "trace":
            links = provenance_tracker.trace(args.target_type, args.target_id)
            if not links:
                print(f"No provenance found for {args.target_type}/{args.target_id}")
            else:
                print(f"Provenance for {args.target_type}/{args.target_id} ({len(links)} sources):\n")
                for l in links:
                    print(f"  ← {l.source_type}/{l.source_id[:16]} [{l.operation}] by {l.agent or '—'}")
        elif args.prov_command == "chain":
            links = provenance_tracker.chain(args.source_type, args.source_id)
            if not links:
                print(f"No outputs derived from {args.source_type}/{args.source_id}")
            else:
                print(f"Outputs from {args.source_type}/{args.source_id} ({len(links)} derived):\n")
                for l in links:
                    print(f"  → {l.target_type}/{l.target_id[:16]} [{l.operation}] by {l.agent or '—'}")
        elif args.prov_command == "lineage":
            steps = provenance_tracker.get_lineage(args.target_type, args.target_id)
            if not steps:
                print(f"No lineage found for {args.target_type}/{args.target_id}")
            else:
                print(f"Lineage for {args.target_type}/{args.target_id} ({len(steps)} hops):\n")
                for i, s in enumerate(steps):
                    print(f"  {i+1}. {s['target_type']}/{s['target_id'][:16]} ← {s['source_type']}/{s['source_id'][:16]} [{s['operation']}]")
                print(f"\n  Root: {steps[-1]['source_type']}/{steps[-1]['source_id'][:16]}")
        elif args.prov_command == "register":
            lid = provenance_tracker.register(
                args.target_type, args.target_id, args.source_type, args.source_id,
                operation=args.operation, agent=args.agent,
                investigation_id=args.investigation,
            )
            print(f"Provenance registered: {lid}")
        elif args.prov_command == "backfill":
            n = provenance_tracker.backfill()
            print(f"Provenance backfill: {n} links created from existing data")
        elif args.prov_command == "stats":
            s = provenance_tracker.stats()
            print(f"Provenance: {s['total']} links")
            if s["by_operation"]:
                print(f"\nBy operation:")
                for op, cnt in s["by_operation"].items():
                    print(f"  {op}: {cnt}")
            if s["by_target_type"]:
                print(f"\nBy target type:")
                for t, cnt in s["by_target_type"].items():
                    print(f"  {t}: {cnt}")
        else:
            prov_parser.print_help()

    elif args.command == "conflicts":
        from cos.memory.conflicts import conflict_detector
        if args.conf_command == "scan":
            n = conflict_detector.scan()
            print(f"Conflict scan: {n} new conflicts detected")
        elif args.conf_command == "list":
            conflicts = conflict_detector.list_conflicts(
                status=args.status, conflict_type=args.type, severity=args.severity)
            if not conflicts:
                print("No conflicts found.")
            else:
                for c in conflicts:
                    print(f"  [{c.severity:>6}] [{c.status:>8}] {c.conflict_type}: {c.description[:70]}")
                    print(f"           ID: {c.id}  A: {c.item_a_id[:12]}  B: {c.item_b_id[:12]}")
        elif args.conf_command == "resolve":
            ok = conflict_detector.resolve(args.conflict_id, args.resolution)
            if ok:
                print(f"Conflict resolved: {args.conflict_id}")
            else:
                print(f"Conflict not found: {args.conflict_id}")
        elif args.conf_command == "stats":
            s = conflict_detector.stats()
            print(f"Conflicts: {s['total']} total")
            if s["by_type"]:
                print(f"\nBy type:")
                for t, cnt in s["by_type"].items():
                    print(f"  {t}: {cnt}")
            if s["by_severity"]:
                print(f"\nBy severity:")
                for sv, cnt in s["by_severity"].items():
                    print(f"  {sv}: {cnt}")
            if s["by_status"]:
                print(f"\nBy status:")
                for st, cnt in s["by_status"].items():
                    print(f"  {st}: {cnt}")
        else:
            conf_parser.print_help()

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
