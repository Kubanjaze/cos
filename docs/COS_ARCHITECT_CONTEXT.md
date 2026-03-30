# COS Architect Context Document

**Prepared for:** Pisces (GPT-5.2) — External Architect
**Prepared by:** Claude Opus 4.6 (build agent)
**Date:** 2026-03-30
**Project version:** 0.5.1
**Repo:** https://github.com/Kubanjaze/cos

---

## 1. What is COS?

**Cognitive Operating System** — a local-first CLI toolkit that ingests information, constructs structured memory, reasons across it, and produces decisions + executable workflows. No server infrastructure. No cloud dependencies. SQLite + filesystem.

**One-sentence goal:** Convert unstructured inputs into structured memory, evaluated hypotheses, and actionable decisions — while compounding knowledge and optimizing cost over time.

---

## 2. Current State (80/120 phases complete — 67%)

| Track | Phases | Status | Package |
|-------|--------|--------|---------|
| **A — Core Infrastructure** | 101-120 | ✅ Complete | `cos/core/` (20 modules) |
| **B — Memory System** | 121-140 | ✅ Complete | `cos/memory/` (20 modules) |
| **C — Reasoning Engine** | 141-160 | ✅ Complete | `cos/reasoning/` (20 modules) |
| **D — Workflow + Automation** | 161-180 | ✅ Complete | `cos/workflow/` (9 modules) |
| **E — Decision Engine** | 181-195 | Not started | `cos/decision/` |
| **F — Interface Layer** | 196-205 | Not started | `cos/interface/` |
| **G — Intelligence Expansion** | 206-215 | Not started | `cos/intelligence/` |
| **H — Autonomy + Optimization** | 216-220 | Not started | `cos/autonomy/` |

**Remaining:** 40 phases across Tracks E-H.

---

## 3. Architecture Decisions (ADRs)

| ADR | Decision | Implication |
|-----|----------|-------------|
| **ADR-001** | Local-first CLI toolkit | No server. `python -m cos <command>`. API-ready interfaces for future migration. |
| **ADR-002** | SQLite + filesystem | Single `~/.cos/cos.db` file. Artifacts stored as files in `~/.cos/artifacts/`. Zero-config. |
| **ADR-003** | Investigation is the primary unit of work | Every operation traces to an Investigation ID. Cross-table aggregation. |
| **ADR-004** | Monorepo with service directories | `cos/{core,memory,reasoning,workflow,decision,interface,intelligence,autonomy}`. One `.venv`, one `pyproject.toml`. |
| **ADR-005** | Evaluation: Quality 40% + Cost 40% + Latency 20% | Benchmark scorecard: `{quality: 0-1, cost: $X, latency_p95: Ns}`. Implemented in Phase 160. |

---

## 4. Completion Gates

| Gate | Checkpoint | Status |
|------|-----------|--------|
| **Gate 1** (~Phase 106) | ingest → normalize → store → tag → retrieve | ✅ PASSED |
| **Gate 2** (~Phase 114) | register + run pipeline → version outputs → logs | ✅ PASSED |
| **Gate 3** (~Phase 132/146/171) | one investigation → ranked outputs + confidence + cost | ✅ All components built, integration pending |
| **Gate 4** (~Phase 205) | minimal UI can browse + rerun + view artifacts | Not started |

---

## 5. Database Schema (33 tables, SQLite)

### Track A — Core (tables 1-7)
| Table | Purpose | Key columns |
|-------|---------|-------------|
| `artifacts` | Ingested files (content-addressable, SHA-256) | id, uri, hash, type, size_bytes, investigation_id |
| `artifact_tags` | Key-value metadata on artifacts | artifact_id, key, value |
| `cost_events` | API cost tracking per model | model, input_tokens, output_tokens, cost_usd |
| `tasks` | Background task queue | command, status, investigation_id |
| `investigations` | Primary unit of work (ADR-003) | id (inv-{8hex}), title, domain, status |
| `versions` | Output versioning per investigation | investigation_id, version_number, description |
| `cache` | TTL-based cache with hit counting | key, value, expires_at, hit_count |

### Track B — Memory (tables 8-23)
| Table | Purpose | Key columns |
|-------|---------|-------------|
| `documents` | Parsed documents from artifacts | id, artifact_id, title, chunk_count |
| `document_chunks` | Text chunks for retrieval | document_id, chunk_index, chunk_text |
| `chunk_embeddings` | Vector embeddings (384-dim, all-MiniLM-L6-v2) | chunk_id, embedding (BLOB) |
| `entities` | Extracted entities (compound, target, activity) | name, entity_type, source_chunk_id, confidence |
| `entity_relations` | Typed edges (has_activity, belongs_to_scaffold) | source_entity, relation_type, target_value |
| `temporal_tags` | Time-aware annotations | target_type, target_id, time_context |
| `episodes` | Episodic memory ("what happened") | episode_type, description, duration_s, cost_usd |
| `concepts` | Semantic memory ("what we know") | name, definition, domain, confidence |
| `procedures` | Procedural memory ("how we do things") | name, steps_json, success_count, fail_count |
| `provenance` | Source traceability (backward+forward) | target_type/id → source_type/id, operation |
| `conflicts` | Detected contradictions | conflict_type, severity, status, resolution |
| `memory_scores` | Composite scoring (relevance+confidence+recency+frequency) | composite_score, weights: 0.3/0.3/0.2/0.2 |
| `cross_links` | Cross-domain concept links | source_domain ↔ target_domain, link_type |
| `memory_snapshots` | Frozen memory state (JSON) | name, snapshot_data |
| `memory_changes` | Incremental update tracking | change_type, status (pending/applied) |
| `connector_log` | External fetch history | connector_name, query, result_count |

### Track C — Reasoning (tables 24-31)
| Table | Purpose | Key columns |
|-------|---------|-------------|
| `syntheses` | Multi-source synthesis results | query, summary, source_count |
| `rankings` | Importance-scored items | context, item_type, item_id, score |
| `hypotheses` | Generated hypotheses | statement, evidence_json, confidence, status |
| `causal_claims` | Causal relationship candidates | cause, effect, mechanism, confidence |
| `scenarios` | Future scenarios | title, assumptions_json, likelihood, impact |
| `insights` | Novel insights extracted | insight_type, description, novelty_score |
| `refinements` | Iterative improvement log | target_type/id, score_before, score_after |
| `benchmark_runs` | ADR-005 tri-metric results | quality_score, cost_usd, latency_p95_s, composite |

### Track D — Workflow (tables 32-35+)
| Table | Purpose | Key columns |
|-------|---------|-------------|
| `workflow_defs` | Workflow DSL definitions | name, steps_json, domain, version |
| `workflow_runs` | Execution state + results | workflow_id, status, steps_json, duration_s |
| `workflow_schedules` | Cron + event triggers | schedule_type, cron_expr, event_type |
| `budgets` | Cost budget constraints | target_type/id, budget_usd, spent_usd |
| `hook_log` | External action execution log | hook_name, status |

---

## 6. Module Inventory (69 Python modules)

### cos/core/ (20 modules) — Infrastructure
`config.py` `logging.py` `cost.py` `ingestion.py` `tagging.py` `tasks.py` `storage.py` `versioning.py` `cli_registry.py` `errors.py` `validation.py` `plugins.py` `pipelines.py` `investigations.py` `events.py` `batch.py` `cache.py` `ratelimit.py` `health.py` `__main__.py`

### cos/memory/ (20 modules) — Knowledge
`documents.py` `embeddings.py` `entities.py` `relations.py` `temporal.py` `episodic.py` `semantic.py` `procedural.py` `graph.py` `provenance.py` `conflicts.py` `scoring.py` `pruning.py` `crossdomain.py` `hybrid_query.py` `snapshots.py` `incremental.py` `connectors.py` `gaps.py` `visualization.py`

### cos/reasoning/ (20 modules) — Intelligence
`synthesis.py` `ranking.py` `contradictions.py` `hypothesis.py` `disconfirmation.py` `uncertainty.py` `evidence.py` `patterns.py` `causal.py` `scenarios.py` `comparison.py` `compression.py` `insights.py` `signal_noise.py` `refinement.py` `multipass.py` `domain_adapters.py` `explainability.py` `cost_optimizer.py` `benchmark.py`

### cos/workflow/ (9 modules) — Automation
`schema.py` `builder.py` `executor.py` `scheduler.py` `orchestrator.py` `templates.py` `budget.py` `analytics.py` `hooks.py`

---

## 7. CLI Surface (45 top-level commands)

```
python -m cos <command> [subcommand] [args]
```

**Core:** `status` `info` `config` `events` `batch` `investigate` `plugins` `pipeline` `ingest` `artifacts` `tag` `search` `storage` `version` `task` `health` `ratelimit` `cache` `cost`

**Memory:** `docs` `embed` `entities` `relations` `temporal` `episodes` `concepts` `procedures` `graph` `provenance` `conflicts` `scores` `prune` `crosslinks` `hybrid` `snapshot` `changes` `connectors` `gaps` `viz`

**Reasoning:** `synthesize` `hypotheses` `reason` (with subcommands: multipass, patterns, contradictions, uncertainty, evidence, insights, signal-noise, compare, causal, scenarios, compress, domain, explain, cost, benchmark, benchmark-history)

**Workflow:** `wf` (with subcommands: define, list, run, runs, replay, templates, instantiate, schedule, schedules, budget, budgets, analytics, benchmark, hooks, hook, marketplace, stats)

---

## 8. Data Flow (end-to-end)

```
File (CSV/PDF/TXT)
  → ingest (content-addressable storage, SHA-256 dedup)
    → document_store (parse + chunk, paragraph-based, max 500 chars)
      → embeddings (all-MiniLM-L6-v2, 384-dim, cosine similarity)
      → entity_extraction (regex NER: compounds, targets, activities, scaffolds)
        → relation_extraction (co-occurrence: has_activity, belongs_to_scaffold)
          → knowledge_graph (BFS traversal, neighbors, paths, subgraphs)
          → provenance (backward: entity→chunk→doc→artifact; forward: artifact→all derived)
            → synthesis (multi-source fusion: concepts + entities + chunks)
              → hypothesis_generation (scaffold-activity SAR patterns)
                → disconfirmation (challenge with counter-evidence)
                  → ranking (multi-factor importance scoring)
                    → workflow_execution (DSL-defined step sequences)
                      → benchmark (ADR-005: quality 40% + cost 40% + latency 20%)
```

---

## 9. Key Verified Results

| Metric | Value |
|--------|-------|
| Entities extracted | 44 (compounds, targets, scaffolds) |
| Relations extracted | 82 (44 scaffold memberships + 38 activity values) |
| Knowledge graph | 44 nodes, 82 edges, 1 connected component, avg degree 3.73 |
| Provenance links | 135 (backfilled from existing FK relationships) |
| Max lineage depth | 3 hops (entity → chunk → document → artifact) |
| Hypotheses generated | 6 scaffold-activity SAR hypotheses |
| Causal claims | 6 (scaffold → bioactivity) |
| System uncertainty | 0.898 overall confidence |
| ADR-005 benchmark | Composite=0.9121 (quality=0.793, cost=$0.01, latency=8ms) |
| Workflow execution | health-check template: 4 steps in 0.028s, 100% success |
| Concepts | 5 across 2 domains (cheminformatics + clinical) |
| Cross-domain links | 1 (CETP: cheminformatics ↔ clinical) |
| Knowledge gaps | 2 (1 low-confidence concept, 1 sparse domain) |

---

## 10. What's Left (Tracks E-H: 40 phases)

### Track E — Decision Engine (Phases 181-195, 15 phases)
Convert reasoning outputs into actionable decisions with risk assessment, tracking, and feedback loops.

**Key phases:**
- 181: Decision object schema (the canonical Decision type)
- 182: Action generation engine
- 183: Risk assessment module
- 184: Invalidation condition generator
- 185-186: Tradeoff analysis + priority ranking
- 189-190: Decision tracking (outcomes vs predictions) + feedback loop
- 195: Decision quality benchmark

**Depends on:** Reasoning outputs (hypotheses, causal claims, scenarios), memory scores, workflow execution.

### Track F — Interface Layer (Phases 196-205, 10 phases)
Make the system usable — investigation browser, chat interface, dashboards, workflow builder UI.

**Key phases:**
- 196: Investigation object UI
- 197: Chat interface (context-aware)
- 198: Workspace dashboard
- 199: Graph visualization UI
- 205: User settings + preferences → **GATE 4 target**

**Depends on:** All of Tracks A-E operational. Can be text-based/CLI initially.

### Track G — Intelligence Expansion (Phases 206-215, 10 phases)
Extend beyond baseline — multi-agent, debate, simulation, knowledge graph reasoning, meta-reasoning.

**Key phases:**
- 206: Multi-agent system
- 207: Agent debate framework
- 208: Simulation engine
- 213: Autonomous hypothesis loop
- 214: Meta-reasoning layer

**Depends on:** Reasoning engine mature, workflow execution reliable.

### Track H — Autonomy + Optimization (Phases 216-220, 5 phases)
Full system independence — self-scheduling, cost optimization AI, continuous monitoring, end-to-end autonomous investigation.

**Key phases:**
- 216: Fully autonomous workflow execution
- 220: End-to-end autonomous investigation loop → **COS completion condition**

**Depends on:** Everything. This is the capstone.

---

## 11. Risks to Watch (from Architect Notes)

1. **Drift risk** — Tracks evolving separate vocabularies. Mitigated: shared schemas (Investigation, Artifact, MemoryItem).
2. **Over-architecture** — No premature cloud/microservices. Validated: SQLite + local works fine at current scale.
3. **No evaluation loop** — Mitigated: ADR-005 benchmark implemented (Phase 160), composite=0.9121.
4. **Autonomy too early** — Tracks G/H deferred until A-F prove reliable.
5. **Provenance gaps** — Mitigated: Phase 130, 135 backfilled links, full 3-hop lineage.

---

## 12. Technology Stack

| Component | Choice |
|-----------|--------|
| Language | Python 3.13 |
| Storage | SQLite (single file: `~/.cos/cos.db`) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2, 384-dim) |
| Entity extraction | Rule-based regex NER (no ML dependency) |
| CLI | argparse with subcommands |
| Build | setuptools + pyproject.toml |
| Platform | Windows 11 (primary), cross-platform compatible |
| External APIs | Anthropic Claude API (cost-tracked, rate-limited) |
| Test data | 45-compound CETP inhibitor library (cheminformatics domain) |

---

## 13. Conventions for New Phases

- **Monorepo**: All code in `cos/{track}/module.py`. Cross-module imports: `from cos.core.config import settings`.
- **Singleton pattern**: Each module exposes a singleton instance (e.g., `memory_scorer = MemoryScorer()`).
- **DB access**: `settings.db_path` → `sqlite3.connect()`. New tables use `CREATE TABLE IF NOT EXISTS`.
- **Logging**: `from cos.core.logging import get_logger; logger = get_logger("cos.track.module")`.
- **CLI**: Add parser in `cos/__main__.py` before `health` command, add handler before `health` handler.
- **IDs**: `{prefix}-{8hex}` format (e.g., `inv-abc12345`, `hyp-def67890`).
- **Timestamps**: ISO-8601 format, `time.strftime("%Y-%m-%dT%H:%M:%S")`.
- **Version numbering**: Increment 0.0.X for each update, roll to 0.X.0 at 9.
