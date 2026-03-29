"""COS CLI entry point — run with `python -m cos`."""

import sys
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import argparse
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
