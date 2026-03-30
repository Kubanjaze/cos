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

    scores_parser = sub.add_parser("scores", help="Memory scoring")
    scores_sub = scores_parser.add_subparsers(dest="scores_command")
    scores_all_p = scores_sub.add_parser("score-all", help="Score all items of a type")
    scores_all_p.add_argument("target_type", help="entity, concept, relation, episode")
    scores_top_p = scores_sub.add_parser("top", help="Top-scored items")
    scores_top_p.add_argument("--type", default=None)
    scores_top_p.add_argument("--limit", type=int, default=10)
    scores_sub.add_parser("stats", help="Scoring statistics")

    prune_parser = sub.add_parser("prune", help="Memory pruning")
    prune_sub = prune_parser.add_subparsers(dest="prune_command")
    prune_ep_p = prune_sub.add_parser("episodes", help="Prune old episodes")
    prune_ep_p.add_argument("--max-age-days", type=int, default=30)
    prune_sub.add_parser("cache", help="Prune expired cache")
    prune_dry_p = prune_sub.add_parser("dry-run", help="Preview pruning")
    prune_dry_p.add_argument("target_type")
    prune_dry_p.add_argument("threshold", type=float)
    prune_sub.add_parser("stats", help="Pruning statistics")

    xlink_parser = sub.add_parser("crosslinks", help="Cross-domain linking")
    xlink_sub = xlink_parser.add_subparsers(dest="xlink_command")
    xlink_sub.add_parser("discover", help="Auto-discover cross-domain links")
    xlink_list_p = xlink_sub.add_parser("list", help="List links")
    xlink_list_p.add_argument("--domain", default=None)
    xlink_sub.add_parser("stats", help="Cross-link statistics")

    hybrid_parser = sub.add_parser("hybrid", help="Hybrid search")
    hybrid_sub = hybrid_parser.add_subparsers(dest="hybrid_command")
    hybrid_search_p = hybrid_sub.add_parser("search", help="Hybrid search query")
    hybrid_search_p.add_argument("query")
    hybrid_search_p.add_argument("--top-k", type=int, default=10)
    hybrid_sub.add_parser("stats", help="Hybrid engine statistics")

    snap_parser = sub.add_parser("snapshot", help="Memory snapshots")
    snap_sub = snap_parser.add_subparsers(dest="snap_command")
    snap_create_p = snap_sub.add_parser("create", help="Create snapshot")
    snap_create_p.add_argument("name")
    snap_create_p.add_argument("--description", default="")
    snap_create_p.add_argument("--investigation", default="default")
    snap_sub.add_parser("list", help="List snapshots")
    snap_show_p = snap_sub.add_parser("show", help="Show snapshot detail")
    snap_show_p.add_argument("snapshot_id")
    snap_sub.add_parser("stats", help="Snapshot statistics")

    changes_parser = sub.add_parser("changes", help="Incremental updates")
    changes_sub = changes_parser.add_subparsers(dest="changes_command")
    changes_sub.add_parser("pending", help="List pending changes")
    changes_sub.add_parser("apply", help="Apply pending changes")
    changes_sub.add_parser("stats", help="Change statistics")

    fetch_parser = sub.add_parser("connectors", help="External connectors")
    fetch_sub = fetch_parser.add_subparsers(dest="fetch_command")
    fetch_sub.add_parser("list", help="List connectors")
    fetch_run_p = fetch_sub.add_parser("fetch", help="Fetch from connector")
    fetch_run_p.add_argument("connector")
    fetch_run_p.add_argument("query")
    fetch_sub.add_parser("stats", help="Connector statistics")

    gaps_parser = sub.add_parser("gaps", help="Knowledge gap detection")
    gaps_sub = gaps_parser.add_subparsers(dest="gaps_command")
    gaps_sub.add_parser("detect", help="Detect all gaps")
    gaps_sub.add_parser("summary", help="Gap summary")

    viz_parser = sub.add_parser("viz", help="Memory visualization")
    viz_sub = viz_parser.add_subparsers(dest="viz_command")
    viz_tree_p = viz_sub.add_parser("tree", help="ASCII tree of entity neighborhood")
    viz_tree_p.add_argument("entity")
    viz_tree_p.add_argument("--depth", type=int, default=1)
    viz_sub.add_parser("map", help="Memory map overview")
    viz_sub.add_parser("clusters", help="Domain clusters")
    viz_export_p = viz_sub.add_parser("export", help="Export graph as JSON")
    viz_export_p.add_argument("--output", default=None, help="Output file path")
    viz_sub.add_parser("stats", help="Visualization statistics")

    # ── Track C: Reasoning Engine ──────────────────────────
    synth_parser = sub.add_parser("synthesize", help="Multi-source synthesis")
    synth_sub = synth_parser.add_subparsers(dest="synth_command")
    synth_run_p = synth_sub.add_parser("run", help="Run synthesis")
    synth_run_p.add_argument("query")
    synth_run_p.add_argument("--investigation", default="default")
    synth_sub.add_parser("list", help="List syntheses")
    synth_sub.add_parser("stats", help="Synthesis statistics")

    hyp_parser = sub.add_parser("hypotheses", help="Hypothesis generation")
    hyp_sub = hyp_parser.add_subparsers(dest="hyp_command")
    hyp_sub.add_parser("generate", help="Generate hypotheses")
    hyp_sub.add_parser("list", help="List hypotheses")
    hyp_challenge_p = hyp_sub.add_parser("challenge", help="Challenge a hypothesis")
    hyp_challenge_p.add_argument("hypothesis_id")
    hyp_refine_p = hyp_sub.add_parser("refine", help="Refine a hypothesis")
    hyp_refine_p.add_argument("hypothesis_id")
    hyp_sub.add_parser("stats", help="Hypothesis statistics")

    reason_parser = sub.add_parser("reason", help="Reasoning operations")
    reason_sub = reason_parser.add_subparsers(dest="reason_command")
    reason_mp_p = reason_sub.add_parser("multipass", help="Multi-pass reasoning")
    reason_mp_p.add_argument("query")
    reason_mp_p.add_argument("--passes", type=int, default=3)
    reason_sub.add_parser("patterns", help="Detect patterns")
    reason_sub.add_parser("contradictions", help="Analyze contradictions")
    reason_sub.add_parser("uncertainty", help="System uncertainty report")
    reason_sub.add_parser("evidence", help="Weight evidence sources")
    reason_sub.add_parser("insights", help="Extract insights")
    reason_sub.add_parser("signal-noise", help="Classify signal vs noise")
    reason_compare_p = reason_sub.add_parser("compare", help="Compare scaffolds")
    reason_compare_p.add_argument("scaffold_a")
    reason_compare_p.add_argument("scaffold_b")
    reason_sub.add_parser("causal", help="Infer causal relationships")
    reason_sub.add_parser("scenarios", help="Generate scenarios")
    reason_compress_p = reason_sub.add_parser("compress", help="Compress domain knowledge")
    reason_compress_p.add_argument("--domain", default="general")
    reason_domain_p = reason_sub.add_parser("domain", help="Domain-specific analysis")
    reason_domain_p.add_argument("domain_name")
    reason_domain_p.add_argument("query")
    reason_sub.add_parser("explain", help="Explainability stats")
    reason_sub.add_parser("cost", help="Reasoning cost analysis")
    reason_sub.add_parser("benchmark", help="Run reasoning benchmark")
    reason_sub.add_parser("benchmark-history", help="Benchmark run history")

    # ── Track D: Workflow + Automation ──────────────────────
    wf_parser = sub.add_parser("wf", help="Workflow operations")
    wf_sub = wf_parser.add_subparsers(dest="wf_command")
    wf_def_p = wf_sub.add_parser("define", help="Define a workflow")
    wf_def_p.add_argument("name")
    wf_def_p.add_argument("steps_json", help="JSON array of steps")
    wf_def_p.add_argument("--description", default="")
    wf_def_p.add_argument("--domain", default="general")
    wf_sub.add_parser("list", help="List workflows")
    wf_run_p = wf_sub.add_parser("run", help="Execute a workflow")
    wf_run_p.add_argument("name")
    wf_run_p.add_argument("--investigation", default="default")
    wf_sub.add_parser("runs", help="List workflow runs")
    wf_replay_p = wf_sub.add_parser("replay", help="Replay/inspect a run")
    wf_replay_p.add_argument("run_id")
    wf_sub.add_parser("templates", help="List workflow templates")
    wf_inst_p = wf_sub.add_parser("instantiate", help="Create workflow from template")
    wf_inst_p.add_argument("template_name")
    wf_inst_p.add_argument("--name", default=None)
    wf_sched_p = wf_sub.add_parser("schedule", help="Schedule a workflow")
    wf_sched_p.add_argument("workflow_name")
    wf_sched_p.add_argument("cron_expr")
    wf_sub.add_parser("schedules", help="List schedules")
    wf_budget_p = wf_sub.add_parser("budget", help="Set cost budget")
    wf_budget_p.add_argument("target_type")
    wf_budget_p.add_argument("target_id")
    wf_budget_p.add_argument("amount", type=float)
    wf_sub.add_parser("budgets", help="List budgets")
    wf_sub.add_parser("analytics", help="Workflow performance report")
    wf_sub.add_parser("benchmark", help="Benchmark workflows")
    wf_sub.add_parser("hooks", help="List action hooks")
    wf_hook_p = wf_sub.add_parser("hook", help="Execute a hook")
    wf_hook_p.add_argument("hook_name")
    wf_sub.add_parser("marketplace", help="Browse workflow marketplace")
    wf_sub.add_parser("stats", help="Workflow statistics")

    # ── Track E: Decision Engine ──────────────────────────
    dec_parser = sub.add_parser("decide", help="Decision engine")
    dec_sub = dec_parser.add_subparsers(dest="dec_command")
    dec_create_p = dec_sub.add_parser("create", help="Create a decision")
    dec_create_p.add_argument("title")
    dec_create_p.add_argument("recommendation")
    dec_create_p.add_argument("--confidence", type=float, default=0.5)
    dec_create_p.add_argument("--investigation", default="default")
    dec_sub.add_parser("list", help="List decisions")
    dec_show_p = dec_sub.add_parser("show", help="Show decision detail")
    dec_show_p.add_argument("decision_id")
    dec_sub.add_parser("generate-actions", help="Generate actions from reasoning")
    dec_sub.add_parser("actions", help="List proposed actions")
    dec_risk_p = dec_sub.add_parser("assess-risk", help="Assess risks for a decision")
    dec_risk_p.add_argument("decision_id")
    dec_tradeoff_p = dec_sub.add_parser("tradeoffs", help="Analyze tradeoffs")
    dec_tradeoff_p.add_argument("decision_id")
    dec_missing_p = dec_sub.add_parser("missing", help="Find missing evidence")
    dec_missing_p.add_argument("decision_id")
    dec_outcome_p = dec_sub.add_parser("outcome", help="Record decision outcome")
    dec_outcome_p.add_argument("decision_id")
    dec_outcome_p.add_argument("outcome")
    dec_outcome_p.add_argument("--type", default="unknown")
    dec_sub.add_parser("calibration", help="Calibration report")
    dec_sub.add_parser("board", help="Scenario board (compare decisions)")
    dec_audit_p = dec_sub.add_parser("audit", help="Decision audit trail")
    dec_audit_p.add_argument("decision_id")
    dec_sub.add_parser("resources", help="Resource allocation suggestions")
    dec_sub.add_parser("benchmark", help="Decision quality benchmark")
    dec_sub.add_parser("stats", help="Decision statistics")

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

    elif args.command == "scores":
        from cos.memory.scoring import memory_scorer
        if args.scores_command == "score-all":
            n = memory_scorer.score_all(args.target_type)
            print(f"Scored {n} {args.target_type} items")
        elif args.scores_command == "top":
            top = memory_scorer.get_top(target_type=args.type, limit=args.limit)
            if not top:
                print("No scores found.")
            else:
                print(f"{'Type':>10} {'ID':>14} {'Composite':>10} {'Relevance':>10} {'Confidence':>10} {'Freq':>5}")
                for s in top:
                    print(f"{s.target_type:>10} {s.target_id[:14]:>14} {s.composite_score:>10.4f} {s.relevance:>10.2f} {s.confidence:>10.2f} {s.frequency:>5}")
        elif args.scores_command == "stats":
            s = memory_scorer.stats()
            print(f"Memory Scores: {s['total']} items, avg={s['avg_score']:.4f}")
            for t, info in s["by_type"].items():
                print(f"  {t}: {info['count']} items, avg={info['avg_score']:.4f}")
        else:
            scores_parser.print_help()

    elif args.command == "prune":
        from cos.memory.pruning import memory_pruner
        if args.prune_command == "episodes":
            n = memory_pruner.prune_episodes(max_age_days=args.max_age_days)
            print(f"Pruned {n} episodes")
        elif args.prune_command == "cache":
            n = memory_pruner.prune_stale_cache()
            print(f"Pruned {n} expired cache entries")
        elif args.prune_command == "dry-run":
            items = memory_pruner.dry_run(args.target_type, args.threshold)
            if not items:
                print(f"No {args.target_type} items below threshold {args.threshold}")
            else:
                print(f"Would prune {len(items)} {args.target_type} items:")
                for item in items[:10]:
                    print(f"  {item['id'][:16]} score={item['score']:.4f}")
        elif args.prune_command == "stats":
            s = memory_pruner.prune_stats()
            print(f"Pruning candidates:")
            print(f"  Expired cache: {s['expired_cache']}")
            print(f"  Total scored: {s['total_scored']}")
            if s["low_score_candidates"]:
                print(f"  Low-score (<0.3):")
                for t, c in s["low_score_candidates"].items():
                    print(f"    {t}: {c}")
        else:
            prune_parser.print_help()

    elif args.command == "crosslinks":
        from cos.memory.crossdomain import cross_linker
        if args.xlink_command == "discover":
            n = cross_linker.discover_links()
            print(f"Discovered {n} cross-domain links")
        elif args.xlink_command == "list":
            links = cross_linker.get_links(domain=args.domain)
            if not links:
                print("No cross-domain links found.")
            else:
                for l in links:
                    print(f"  {l.source_domain}/{l.source_id[:12]} --[{l.link_type}]--> {l.target_domain}/{l.target_id[:12]} (conf={l.confidence:.2f})")
        elif args.xlink_command == "stats":
            s = cross_linker.stats()
            print(f"Cross-links: {s['total']} total")
            if s["domains_linked"]:
                print(f"  Domains: {', '.join(s['domains_linked'])}")
            for t, c in s["by_type"].items():
                print(f"  {t}: {c}")
        else:
            xlink_parser.print_help()

    elif args.command == "hybrid":
        from cos.memory.hybrid_query import hybrid_engine
        if args.hybrid_command == "search":
            results = hybrid_engine.search(args.query, top_k=args.top_k)
            if not results:
                print(f"No results for '{args.query}'")
            else:
                print(f"Hybrid search: '{args.query}' ({len(results)} results)\n")
                for i, r in enumerate(results, 1):
                    sources = "+".join(r["sources"])
                    print(f"  {i}. [{r['type']:>8}] {r['name'][:25]:>25} score={r['fused_score']:.4f} ({sources})")
                    if r.get("text"):
                        print(f"     {r['text'][:70]}")
        elif args.hybrid_command == "stats":
            s = hybrid_engine.stats()
            print(f"Hybrid Query Engine:")
            print(f"  Concepts:   {s['searchable_concepts']}")
            print(f"  Chunks:     {s['searchable_chunks']}")
            print(f"  Entities:   {s['searchable_entities']}")
            print(f"  Relations:  {s['searchable_relations']}")
            print(f"  Embeddings: {s['vector_embeddings']}")
            print(f"  Weights:    vector={s['weights']['vector']}, keyword={s['weights']['keyword']}, graph={s['weights']['graph']}")
        else:
            hybrid_parser.print_help()

    elif args.command == "snapshot":
        from cos.memory.snapshots import snapshot_manager
        if args.snap_command == "create":
            sid = snapshot_manager.create(args.name, description=args.description, investigation_id=args.investigation)
            print(f"Snapshot created: {sid} — {args.name}")
        elif args.snap_command == "list":
            snaps = snapshot_manager.list_snapshots()
            if not snaps:
                print("No snapshots.")
            else:
                for s in snaps:
                    print(f"  {s.id}  {s.created_at}  {s.name}")
        elif args.snap_command == "show":
            import json as _json
            s = snapshot_manager.get(args.snapshot_id)
            if not s:
                print(f"Snapshot not found: {args.snapshot_id}")
            else:
                data = _json.loads(s.snapshot_data)
                print(f"Snapshot: {s.name} ({s.id})")
                print(f"  Created: {s.created_at}")
                print(f"  Investigation: {s.investigation_id}")
                print(f"\n  Counts:")
                for table, count in data.get("counts", {}).items():
                    print(f"    {table}: {count}")
        elif args.snap_command == "stats":
            s = snapshot_manager.stats()
            print(f"Snapshots: {s['total_snapshots']}")
        else:
            snap_parser.print_help()

    elif args.command == "changes":
        from cos.memory.incremental import update_tracker
        if args.changes_command == "pending":
            pending = update_tracker.get_pending()
            if not pending:
                print("No pending changes.")
            else:
                for c in pending:
                    print(f"  {c.id}  [{c.change_type}] {c.target_type}/{c.target_id[:12]} — {c.created_at}")
        elif args.changes_command == "apply":
            n = update_tracker.apply_pending()
            print(f"Applied {n} pending changes")
        elif args.changes_command == "stats":
            s = update_tracker.stats()
            print(f"Memory Changes: {s['total']} total")
            for st, cnt in s["by_status"].items():
                print(f"  {st}: {cnt}")
        else:
            changes_parser.print_help()

    elif args.command == "connectors":
        from cos.memory.connectors import connector_registry
        if args.fetch_command == "list":
            conns = connector_registry.list_connectors()
            for c in conns:
                status = "enabled" if c.enabled else "disabled"
                print(f"  {c.name:>12} [{status}] {c.domain:>15} — {c.description}")
        elif args.fetch_command == "fetch":
            try:
                results = connector_registry.fetch(args.connector, args.query)
                print(f"Fetched {len(results)} results from '{args.connector}':")
                for r in results[:5]:
                    print(f"  {r}")
            except Exception as e:
                print(f"Error: {e}")
        elif args.fetch_command == "stats":
            s = connector_registry.stats()
            print(f"Connectors: {s['registered']} registered, {s['total_fetches']} total fetches")
            for n, info in s["by_connector"].items():
                print(f"  {n}: {info['fetches']} fetches, {info['results']} results")
        else:
            fetch_parser.print_help()

    elif args.command == "gaps":
        from cos.memory.gaps import gap_detector
        if args.gaps_command == "detect":
            gaps = gap_detector.detect_all()
            print("Knowledge Gaps Detected:\n")
            print(f"  Unlinked entities:     {len(gaps['unlinked_entities'])}")
            for e in gaps["unlinked_entities"][:5]:
                print(f"    {e['name']} ({e['type']})")
            print(f"  Low confidence concepts: {len(gaps['low_confidence_concepts'])}")
            for c in gaps["low_confidence_concepts"][:5]:
                print(f"    {c['name']} ({c['domain']}) conf={c['confidence']:.2f}")
            print(f"  Orphan chunks:         {len(gaps['orphan_chunks'])}")
            print(f"  Missing provenance:    {len(gaps['missing_provenance'])}")
            print(f"  Sparse domains:        {len(gaps['sparse_domains'])}")
            for d in gaps["sparse_domains"]:
                print(f"    {d['domain']}: {d['concept_count']} concepts")
        elif args.gaps_command == "summary":
            s = gap_detector.summary()
            print(f"Knowledge Gap Summary: {s['total_gaps']} total gaps")
            for k, v in s.items():
                if k != "total_gaps":
                    print(f"  {k}: {v}")
        else:
            gaps_parser.print_help()

    elif args.command == "viz":
        from cos.memory.visualization import memory_viz
        if args.viz_command == "tree":
            tree = memory_viz.graph_ascii(args.entity, depth=args.depth)
            print(tree)
        elif args.viz_command == "map":
            print(memory_viz.memory_map())
        elif args.viz_command == "clusters":
            clusters = memory_viz.domain_clusters()
            for domain, concepts in clusters.items():
                print(f"\n  {domain} ({len(concepts)} concepts):")
                for c in concepts:
                    print(f"    {c['name']:>25} conf={c['confidence']:.2f}")
        elif args.viz_command == "export":
            data = memory_viz.export_graph()
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(data)
                print(f"Graph exported to {args.output}")
            else:
                print(data[:500] + "..." if len(data) > 500 else data)
        elif args.viz_command == "stats":
            s = memory_viz.stats()
            print(f"Visualization: {s['entities']} entities, {s['relations']} relations, {s['concepts']} concepts")
        else:
            viz_parser.print_help()

    # ── Track C: Reasoning Handlers ──────────────────────────
    elif args.command == "synthesize":
        from cos.reasoning.synthesis import synthesis_engine
        if args.synth_command == "run":
            syn = synthesis_engine.synthesize(args.query, investigation_id=args.investigation)
            print(f"Synthesis: '{syn.query}' ({syn.source_count} sources)\n")
            print(f"  {syn.summary}")
            for s in syn.sources[:5]:
                print(f"  [{s['type']:>8}] {s.get('name','')[:25]} (conf={s.get('confidence',0):.2f})")
        elif args.synth_command == "list":
            for s in synthesis_engine.list_syntheses():
                print(f"  {s['id']}  {s['query'][:30]:>30}  {s['sources']} sources  {s['created_at']}")
        elif args.synth_command == "stats":
            s = synthesis_engine.stats()
            print(f"Syntheses: {s['total']} total, avg {s['avg_sources']} sources")
        else:
            synth_parser.print_help()

    elif args.command == "hypotheses":
        from cos.reasoning.hypothesis import hypothesis_generator
        if args.hyp_command == "generate":
            hyps = hypothesis_generator.generate()
            print(f"Generated {len(hyps)} hypotheses:")
            for h in hyps:
                print(f"  {h['id']}  conf={h['confidence']:.2f}  {h['statement'][:70]}")
        elif args.hyp_command == "list":
            for h in hypothesis_generator.list_hypotheses():
                print(f"  [{h['status']:>8}] conf={h['confidence']:.2f}  {h['statement'][:60]}")
        elif args.hyp_command == "challenge":
            from cos.reasoning.disconfirmation import disconfirmation_engine
            result = disconfirmation_engine.challenge(args.hypothesis_id)
            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                print(f"Challenge: {result['statement'][:60]}")
                print(f"  Original confidence: {result['original_confidence']:.3f}")
                print(f"  Challenges found: {result['challenge_count']}")
                print(f"  Adjusted confidence: {result['adjusted_confidence']:.3f}")
                for c in result["challenges"]:
                    print(f"    - [{c['type']}] {c['detail']}")
        elif args.hyp_command == "refine":
            from cos.reasoning.refinement import refinement_loop
            result = refinement_loop.refine_hypothesis(args.hypothesis_id)
            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                print(f"Refined: iteration {result['iteration']}, {result['confidence_before']:.3f} → {result['confidence_after']:.3f}")
        elif args.hyp_command == "stats":
            s = hypothesis_generator.stats()
            print(f"Hypotheses: {s['total']} total, avg confidence={s['avg_confidence']:.3f}")
            for st, cnt in s["by_status"].items():
                print(f"  {st}: {cnt}")
        else:
            hyp_parser.print_help()

    elif args.command == "reason":
        if args.reason_command == "multipass":
            from cos.reasoning.multipass import multipass_reasoner
            result = multipass_reasoner.reason(args.query, passes=args.passes)
            print(f"Multi-pass reasoning: '{args.query}' ({result['total_passes']} passes, {result['total_duration_s']:.3f}s)")
            for p in result["passes"]:
                actions = ", ".join(f"{a['type']}" for a in p["actions"])
                print(f"  Pass {p['pass']}: {actions} ({p['duration_s']:.3f}s)")
        elif args.reason_command == "patterns":
            from cos.reasoning.patterns import pattern_detector
            s = pattern_detector.stats()
            print(f"Patterns: {s['scaffold_patterns']} scaffold, {s['relation_types']} relation types, {s['entity_types']} entity types, {s['domains']} domains")
            for p in pattern_detector.scaffold_activity_patterns():
                print(f"  {p['scaffold']:>6}: {p['compounds']} compounds, avg pIC50={p['avg_pIC50']:.2f}, spread={p['spread']:.2f} ({p['trend']})")
        elif args.reason_command == "contradictions":
            from cos.reasoning.contradictions import contradiction_analyzer
            analyses = contradiction_analyzer.analyze()
            print(f"Contradiction analysis: {len(analyses)} open conflicts")
            for a in analyses:
                print(f"  [{a['severity']:>6}] {a['description'][:60]}")
                print(f"          Suggestion: {a['suggestion']}")
        elif args.reason_command == "uncertainty":
            from cos.reasoning.uncertainty import uncertainty_estimator
            s = uncertainty_estimator.system_uncertainty()
            print(f"System Uncertainty Report:")
            for k, v in s.items():
                print(f"  {k}: {v}")
        elif args.reason_command == "evidence":
            from cos.reasoning.evidence import evidence_weighter
            sources = evidence_weighter.weight_sources()
            print(f"Evidence sources ({len(sources)}):")
            for s in sources:
                print(f"  {s['name']:>15} weight={s['weight']:.3f} entities={s['entities']} relations={s['relations']}")
        elif args.reason_command == "insights":
            from cos.reasoning.insights import insight_extractor
            insights = insight_extractor.extract()
            print(f"Insights: {len(insights)} found")
            for i in insights:
                print(f"  [{i['type']:>16}] novelty={i['novelty']:.2f} — {i['description'][:60]}")
        elif args.reason_command == "signal-noise":
            from cos.reasoning.signal_noise import signal_noise_classifier
            s = signal_noise_classifier.stats()
            print(f"Signal/Noise: entities={s['entity_signal']} signal / {s['entity_noise']} noise, concepts={s['concept_signal']} signal / {s['concept_noise']} noise")
        elif args.reason_command == "compare":
            from cos.reasoning.comparison import comparison_engine
            result = comparison_engine.compare_scaffolds(args.scaffold_a, args.scaffold_b)
            for key in ["a", "b"]:
                p = result[key]
                print(f"  {p['scaffold']:>6}: {p['compounds']} compounds, avg pIC50={p['avg_pIC50']}, max={p['max_pIC50']}")
            print(f"  Winner: {result['winner']} (margin={result['margin']})")
        elif args.reason_command == "causal":
            from cos.reasoning.causal import causal_inference
            claims = causal_inference.infer()
            print(f"Causal claims: {len(claims)}")
            for c in claims:
                print(f"  {c['cause']} → {c['effect']} ({c['mechanism']}) conf={c['confidence']:.2f}")
        elif args.reason_command == "scenarios":
            from cos.reasoning.scenarios import scenario_generator
            scenarios = scenario_generator.generate()
            print(f"Scenarios: {len(scenarios)}")
            for s in scenarios:
                print(f"  [{s['impact']:>6}] likelihood={s['likelihood']:.1f} — {s['title']}")
        elif args.reason_command == "compress":
            from cos.reasoning.compression import compression_engine
            result = compression_engine.compress_domain(args.domain)
            print(f"Domain: {result['domain']} ({result['concept_count']} concepts)")
            print(f"  {result['summary']}")
        elif args.reason_command == "domain":
            from cos.reasoning.domain_adapters import domain_adapter_registry
            result = domain_adapter_registry.analyze(args.domain_name, args.query)
            print(f"Domain analysis ({result['adapter']}):")
            for k, v in result.items():
                if k not in ("adapter", "query"):
                    print(f"  {k}: {v}")
        elif args.reason_command == "explain":
            from cos.reasoning.explainability import explainability_layer
            s = explainability_layer.stats()
            print(f"Explainability: {s['explainable_hypotheses']} hypotheses, {s['explainable_scores']} scores, {s['explainable_conflicts']} conflicts")
        elif args.reason_command == "cost":
            from cos.reasoning.cost_optimizer import reasoning_cost_optimizer
            result = reasoning_cost_optimizer.analyze_costs()
            print(f"Reasoning Cost Analysis:")
            print(f"  Total API cost: ${result['total_api_cost']:.4f}")
            print(f"  API calls: {result['api_calls']}")
            print(f"  Syntheses: {result['syntheses']}")
            for r in result["recommendations"]:
                print(f"  → {r}")
        elif args.reason_command == "benchmark":
            from cos.reasoning.benchmark import reasoning_benchmark
            result = reasoning_benchmark.run_benchmark()
            print(f"Benchmark: {result['name']} (composite={result['composite']:.4f})")
            print(f"  Quality:  {result['quality']:.4f} (40% → {result['scorecard']['quality_40pct']:.4f})")
            print(f"  Cost:     ${result['cost_usd']:.4f} (40% → {result['scorecard']['cost_40pct']:.4f})")
            print(f"  Latency:  {result['latency_p95_s']:.3f}s (20% → {result['scorecard']['latency_20pct']:.4f})")
            print(f"  Duration: {result['duration_s']:.3f}s")
        elif args.reason_command == "benchmark-history":
            from cos.reasoning.benchmark import reasoning_benchmark
            runs = reasoning_benchmark.list_runs()
            if not runs:
                print("No benchmark runs.")
            else:
                print(f"{'Composite':>10} {'Quality':>8} {'Cost':>8} {'Latency':>8} Created")
                for r in runs:
                    print(f"{r['composite']:>10.4f} {r['quality']:>8.4f} ${r['cost']:>7.4f} {r['latency']:>7.3f}s {r['created_at']}")
        else:
            reason_parser.print_help()

    # ── Track D: Workflow Handlers ──────────────────────────
    elif args.command == "wf":
        if args.wf_command == "define":
            import json as _json
            from cos.workflow.schema import workflow_schema
            try:
                steps = _json.loads(args.steps_json)
                wid = workflow_schema.define(args.name, steps, description=args.description, domain=args.domain)
                print(f"Workflow defined: {wid} — {args.name} ({len(steps)} steps)")
            except Exception as e:
                print(f"Error: {e}")
        elif args.wf_command == "list":
            from cos.workflow.schema import workflow_schema
            wfs = workflow_schema.list_workflows()
            if not wfs:
                print("No workflows defined.")
            else:
                for w in wfs:
                    print(f"  {w['name']:>25} v{w['version']} ({w['domain']}) — {w['description'][:40]}")
        elif args.wf_command == "run":
            from cos.workflow.executor import workflow_executor
            try:
                result = workflow_executor.execute(args.name, investigation_id=args.investigation)
                print(f"\nWorkflow: {result['workflow']} — {result['status']} ({result['duration_s']:.3f}s)")
                for s in result["steps"]:
                    status = "OK" if s["status"] == "completed" else s["status"].upper()
                    print(f"  {s.get('name','step'):>20} [{status}] {s['duration_s']:.3f}s")
            except Exception as e:
                print(f"Error: {e}")
        elif args.wf_command == "runs":
            from cos.workflow.executor import workflow_executor
            runs = workflow_executor.list_runs()
            if not runs:
                print("No workflow runs.")
            else:
                for r in runs:
                    print(f"  {r['id']}  {r['workflow']:>20}  {r['status']:>10}  {r['duration_s']:.3f}s  {r['started']}")
        elif args.wf_command == "replay":
            from cos.workflow.analytics import workflow_analytics
            result = workflow_analytics.replay_run(args.run_id)
            if "error" in result and isinstance(result["error"], str) and result.get("run_id") is None:
                print(f"Error: {result['error']}")
            else:
                print(f"Run: {result.get('run_id','')} — {result.get('workflow','')} ({result.get('status','')})")
                for s in result.get("steps", []):
                    print(f"  Step {s.get('step','')}: {s.get('name','')} [{s.get('status','')}] {s.get('duration_s',0):.3f}s")
        elif args.wf_command == "templates":
            from cos.workflow.templates import template_registry
            for t in template_registry.list_templates():
                print(f"  {t['name']:>20} ({t['steps']} steps) — {t['description']}")
        elif args.wf_command == "instantiate":
            from cos.workflow.templates import template_registry
            try:
                wid = template_registry.instantiate(args.template_name, workflow_name=args.name)
                print(f"Workflow created from template: {wid}")
            except Exception as e:
                print(f"Error: {e}")
        elif args.wf_command == "schedule":
            from cos.workflow.scheduler import workflow_scheduler
            sid = workflow_scheduler.schedule(args.workflow_name, args.cron_expr)
            print(f"Scheduled: {sid}")
        elif args.wf_command == "schedules":
            from cos.workflow.scheduler import workflow_scheduler
            for s in workflow_scheduler.list_schedules():
                print(f"  {s['workflow']:>20} [{s['type']}] {'enabled' if s['enabled'] else 'disabled'} {s.get('cron','') or s.get('event','')}")
        elif args.wf_command == "budget":
            from cos.workflow.budget import budget_manager
            bid = budget_manager.set_budget(args.target_type, args.target_id, args.amount)
            print(f"Budget set: {bid} — {args.target_type}/{args.target_id} = ${args.amount:.2f}")
        elif args.wf_command == "budgets":
            from cos.workflow.budget import budget_manager
            for b in budget_manager.list_budgets():
                print(f"  {b['type']:>12}/{b['id'][:12]} budget=${b['budget']:.2f} spent=${b['spent']:.4f} [{b['status']}]")
        elif args.wf_command == "analytics":
            from cos.workflow.analytics import workflow_analytics
            report = workflow_analytics.performance_report()
            if not report["workflows"]:
                print("No workflow data yet.")
            else:
                print(f"{'Workflow':>25} {'Runs':>5} {'OK%':>6} {'Avg(s)':>7}")
                for w in report["workflows"]:
                    print(f"{w['name']:>25} {w['runs']:>5} {w['success_rate']:>5.0%} {w['avg_duration_s']:>7.3f}")
        elif args.wf_command == "benchmark":
            from cos.workflow.analytics import workflow_analytics
            result = workflow_analytics.benchmark_workflows()
            if not result["benchmarks"]:
                print("No benchmarks yet.")
            else:
                for b in result["benchmarks"]:
                    print(f"  {b['workflow']:>25} composite={b['composite']:.4f} sr={b['success_rate']:.0%} avg={b['avg_duration_s']:.3f}s")
        elif args.wf_command == "hooks":
            from cos.workflow.hooks import hook_registry
            for h in hook_registry.list_hooks():
                print(f"  {h}")
        elif args.wf_command == "hook":
            from cos.workflow.hooks import hook_registry
            result = hook_registry.execute(args.hook_name)
            print(f"Hook '{args.hook_name}': {result['status']}")
            if result.get("result"):
                for k, v in result["result"].items():
                    print(f"  {k}: {v}")
        elif args.wf_command == "marketplace":
            from cos.workflow.hooks import workflow_marketplace
            items = workflow_marketplace.list_available()
            if not items:
                print("No items in marketplace.")
            else:
                for i in items:
                    print(f"  [{i['type']:>8}] {i['name']:>25} — {i['description'][:40]}")
        elif args.wf_command == "stats":
            from cos.workflow.executor import workflow_executor
            from cos.workflow.schema import workflow_schema
            from cos.workflow.templates import template_registry
            ws = workflow_schema.stats()
            es = workflow_executor.stats()
            ts_stat = template_registry.stats()
            print(f"Workflow System:")
            print(f"  Definitions: {ws['total_workflows']}")
            print(f"  Templates:   {ts_stat['total_templates']}")
            print(f"  Runs:        {es['total_runs']} (ok={es['completed']}, fail={es['failed']})")
            print(f"  Success rate:{es['success_rate']:.0%}" if es['total_runs'] > 0 else "  Success rate: —")
        else:
            wf_parser.print_help()

    # ── Track E: Decision Handlers ──────────────────────────
    elif args.command == "decide":
        if args.dec_command == "create":
            from cos.decision.schema import decision_store
            did = decision_store.create(args.title, args.recommendation,
                                         confidence=args.confidence, investigation_id=args.investigation)
            print(f"Decision created: {did} — {args.title}")
        elif args.dec_command == "list":
            from cos.decision.schema import decision_store
            decs = decision_store.list_decisions()
            if not decs:
                print("No decisions.")
            else:
                for d in decs:
                    print(f"  [{d.status:>10}] conf={d.confidence:.2f}  {d.title[:50]}  ({d.id})")
        elif args.dec_command == "show":
            from cos.decision.schema import decision_store
            d = decision_store.get(args.decision_id)
            if not d:
                print(f"Decision not found: {args.decision_id}")
            else:
                print(f"Decision: {d.title}")
                print(f"  ID:             {d.id}")
                print(f"  Status:         {d.status}")
                print(f"  Confidence:     {d.confidence:.2f}")
                print(f"  Recommendation: {d.recommendation}")
                print(f"  Actions:        {len(d.actions)}")
                print(f"  Risks:          {len(d.risks)}")
                print(f"  Invalidations:  {len(d.invalidation_conditions)}")
        elif args.dec_command == "generate-actions":
            from cos.decision.actions import action_generator
            actions = action_generator.generate()
            print(f"Generated {len(actions)} actions:")
            for a in actions:
                print(f"  #{a['rank']} [{a['type']:>16}] priority={a['priority']:.3f} — {a['description'][:55]}")
        elif args.dec_command == "actions":
            from cos.decision.actions import action_generator
            for a in action_generator.list_actions():
                print(f"  [{a['status']:>8}] priority={a['priority']:.3f} {a['type']:>16} — {a['description'][:50]}")
        elif args.dec_command == "assess-risk":
            from cos.decision.risk import risk_assessor
            risks = risk_assessor.assess(args.decision_id)
            print(f"Risk assessment ({len(risks)} risks):")
            for r in risks:
                if "error" in r:
                    print(f"  Error: {r['error']}")
                else:
                    print(f"  [{r['impact']:>6}] {r['type']}: {r['description'][:55]}")
                    print(f"          Mitigation: {r['mitigation'][:55]}")
                    if r.get("invalidation"):
                        print(f"          Invalidates if: {r['invalidation'][:55]}")
        elif args.dec_command == "tradeoffs":
            from cos.decision.tradeoffs import tradeoff_analyzer
            result = tradeoff_analyzer.analyze(args.decision_id)
            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                print(f"Tradeoff Analysis: {result['title']}")
                print(f"  Pros: {', '.join(result['pros'][:3])}")
                print(f"  Cons: {', '.join(result['cons'][:3])}")
                print(f"  Confidence: {result['original_confidence']:.2f} → {result['adjusted_confidence']:.2f}")
                print(f"  Recommendation: {result['recommendation']}")
        elif args.dec_command == "missing":
            from cos.decision.missing_evidence import missing_evidence_detector
            gaps = missing_evidence_detector.detect(args.decision_id)
            print(f"Missing evidence ({len(gaps)} gaps):")
            for g in gaps:
                if "error" in g:
                    print(f"  Error: {g['error']}")
                else:
                    print(f"  [{g['severity']:>6}] {g['type']}: {g['description'][:60]}")
                    print(f"          → {g['suggestion']}")
        elif args.dec_command == "outcome":
            from cos.decision.tracking import decision_tracker
            try:
                oid = decision_tracker.record_outcome(args.decision_id, args.outcome, outcome_type=args.type)
                print(f"Outcome recorded: {oid}")
            except ValueError as e:
                print(f"Error: {e}")
        elif args.dec_command == "calibration":
            from cos.decision.tracking import decision_tracker
            report = decision_tracker.calibration_report()
            print(f"Decision Calibration:")
            for k, v in report.items():
                print(f"  {k}: {v}")
        elif args.dec_command == "board":
            from cos.decision.tracking import decision_tracker
            board = decision_tracker.scenario_board()
            if not board:
                print("No proposed decisions.")
            else:
                print(f"{'Title':>35} {'Conf':>6} {'Actions':>7} {'Risks':>6}")
                for d in board:
                    print(f"{d['title'][:35]:>35} {d['confidence']:>6.2f} {d['actions']:>7} {d['risks']:>6}")
        elif args.dec_command == "audit":
            from cos.decision.tracking import decision_tracker
            trail = decision_tracker.get_audit_trail(args.decision_id)
            if not trail:
                print(f"No audit trail for {args.decision_id}")
            else:
                for entry in trail:
                    print(f"  {entry['created_at']} [{entry['actor']}] {entry['action']}: {entry['details'][:50]}")
        elif args.dec_command == "resources":
            from cos.decision.tracking import decision_tracker
            allocs = decision_tracker.allocate_resources()
            if not allocs:
                print("No decisions to allocate resources to.")
            else:
                for a in allocs:
                    print(f"  {a['title'][:30]:>30} conf={a['confidence']:.2f} → {a['suggested_effort']}")
        elif args.dec_command == "benchmark":
            from cos.decision.benchmark import decision_benchmark
            result = decision_benchmark.run()
            print(f"Decision Benchmark (composite={result['composite']:.4f}):")
            print(f"  Total decisions: {result['total_decisions']}")
            print(f"  Avg confidence:  {result['avg_confidence']:.3f}")
            print(f"  With risks:      {result['with_risks']}")
            print(f"  With evidence:   {result['with_evidence']}")
            print(f"  Outcome accuracy:{result['outcome_accuracy']:.3f}")
            for k, v in result["breakdown"].items():
                print(f"    {k}: {v:.4f}")
        elif args.dec_command == "stats":
            from cos.decision.schema import decision_store
            s = decision_store.stats()
            print(f"Decisions: {s['total']} total, avg confidence={s['avg_confidence']:.3f}")
            for st, cnt in s["by_status"].items():
                print(f"  {st}: {cnt}")
        else:
            dec_parser.print_help()

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
