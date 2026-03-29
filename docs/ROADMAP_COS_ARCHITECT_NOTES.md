# COS Roadmap — Architect Notes (Non-binding)

**Purpose of this doc:** Provide implementation considerations, open questions, and optional guardrails.
**Non-binding:** Nothing here overrides ROADMAP_COS.md. The team may accept, modify, or reject any item.

---

## 1) The 5 architecture questions to answer early

1. **System boundary (v0):** Is the initial COS a local-first CLI toolkit, a long-running service, or a hybrid?
2. **Storage posture:** Filesystem + SQLite first, or a dedicated DB from day one?
3. **Primary unit of work:** What is the canonical object — Investigation, WorkflowRun, or something else?
4. **Build style:** Monorepo vs multi-repo? Packages vs services? How strict is separation in Phase 101?
5. **Evaluation:** What is the minimal benchmark loop that tells us the system is improving (quality + cost + latency)?

---

## 2) Definition of Done template (optional but high-leverage)

A phase can be considered complete when it has:

- **Runnable artifact** (CLI command that works on sample inputs)
- **Stable outputs** (schema + version)
- **Verification checklist** (expected outputs + failure modes)
- **Observability** (logs + timing; cost if applicable)
- **Reproducibility note** (how to re-run + where outputs go)

*Why this helps:* Reduces phase completion ambiguity and prevents shipping phases that are conceptual-only.

---

## 3) Minimal core schemas (field lists, not locked implementations)

These schemas are suggested as *shared language* between Tracks. Keep them lightweight until the team decides to formalize.

### Investigation
- id, question/title, domain, tags
- inputs[] (references to Artifacts)
- outputs[] (references to Artifacts)
- created_at, updated_at, status

### Artifact
- id, type (file/text/json/db table), uri/path
- hash, schema_version
- produced_by (workflow_id + step_id), created_at

### MemoryItem
- id, kind (episodic/semantic/procedural)
- content_ref (pointer to raw text/chunk)
- provenance_ref (Artifact/source reference)
- timestamp, confidence, relevance

### WorkflowRun
- id, workflow_id, steps[], step_status[]
- logs_ref, metrics (time/cost/tokens)
- outputs[] (Artifacts)

### Decision
- id, recommendation
- actions[] (typed)
- evidence_refs[] (MemoryItems/Artifacts)
- confidence, risks[]
- invalidation_conditions[]

*Why this helps:* Prevents Tracks A/B/C/D/E from drifting into incompatible definitions.

---

## 4) Vertical slice gates (integration checkpoints, not extra phases)

Optional milestones to ensure progress produces usable end-to-end capability:

- **Gate 1 (around Phase 105):** ingest → normalize → store → tag → retrieve by metadata
- **Gate 2 (around Phase 114–116):** register + run a pipeline → version outputs → show logs
- **Gate 3 (around Phase 132/146/171):** one investigation → ranked outputs + confidence + cost report
- **Gate 4 (around Phase 205):** minimal UI can browse investigations + rerun workflows + view artifacts

*Why this helps:* Keeps the system integrated rather than finishing entire tracks in isolation.

---

## 5) Sequencing considerations (options, not directives)

### Track A sequencing
- Config + logging/tracing before cost tracking (cost is emitted as a trace/log event).
- Storage abstraction can start with "local-only interface" and add cloud backends later.

### Track F sequencing
- UI can begin as a "viewer + runner" once schemas stabilize, rather than a full workflow builder immediately.

---

## 6) Risks to watch

1. **Drift risk:** Tracks evolve separate vocabularies (different meanings of Investigation/Artifact/Memory).
2. **Over-architecture early:** Premature microservices or premature cloud adds complexity before product value exists.
3. **No evaluation loop:** If "improving system intelligence" is not measurable, phases won't compound.
4. **Autonomy too early:** Scaling agents before audit/budget/evaluation can scale confident wrongness + cost.
5. **Provenance gaps:** If sources aren't traceable, outputs won't be trusted.

---

## 7) ADR-lite template

Use this to record architectural decisions as they happen, without freezing the roadmap.

```
ADR-XXX: <Title>
Date:
Context:
Decision:
Options considered:
Tradeoffs:
Impact on roadmap phases:
Verification / success criteria:
Revisit triggers:
```

*Why this helps:* Captures decisions as they happen without turning the roadmap into a prescriptive implementation spec.

---

## ADR log

| ADR | Title | Date | Status |
|---|---|---|---|
| ADR-001 | System boundary | 2026-03-27 | Decided |
| ADR-002 | Storage posture | 2026-03-27 | Decided |
| ADR-003 | Primary unit of work | 2026-03-27 | Decided |
| ADR-004 | Build style | 2026-03-27 | Decided |
| ADR-005 | Evaluation framework | 2026-03-27 | Decided |

---

### ADR-001: System Boundary
**Date:** 2026-03-27
**Context:** Need to decide if COS v0 is a local CLI toolkit, long-running service, or hybrid.
**Decision:** Local-first CLI toolkit with interfaces designed to allow API/service use later.
**Options considered:** (A) Local CLI, (B) Long-running service, (C) Hybrid
**Tradeoffs:** Local-first saves on hosting costs and complexity. Abstractions should be service-ready (e.g., function signatures that could become API endpoints) but no actual server infrastructure until needed.
**Impact on roadmap phases:** Phase 110 (CLI → service transition) becomes a future migration point, not a day-one requirement. Phases 101-109 build pure CLI tools.
**Verification:** All phases 101-120 should run via `python main.py` or `python -m cos.<module>` without any running server.
**Revisit triggers:** If multi-user access or real-time ingestion is needed.

---

### ADR-002: Storage Posture
**Date:** 2026-03-27
**Context:** Need to decide between SQLite + filesystem vs dedicated DB.
**Decision:** SQLite + filesystem first. Same approach as Phase 88.
**Options considered:** (A) SQLite + filesystem, (B) PostgreSQL from day one
**Tradeoffs:** SQLite is zero-config, portable, and sufficient for single-user local-first system. Filesystem for raw files + SQLite for structured data. Cloud/Postgres migration is a future phase if needed.
**Impact on roadmap phases:** Phase 108 (storage abstraction) should define an interface layer that is backend-agnostic, even though initial implementation is SQLite.
**Verification:** All data persists in `~/.cos/` or project-local directories. No external DB processes required.
**Revisit triggers:** If concurrent access, multi-user, or dataset size >10GB becomes necessary.

---

### ADR-003: Primary Unit of Work
**Date:** 2026-03-27
**Context:** Need a canonical object that everything revolves around.
**Decision:** Investigation is the primary unit of work.
**Options considered:** Investigation, WorkflowRun, Artifact
**Tradeoffs:** Investigation is the highest-level object — it encapsulates a question, the workflows run to answer it, the artifacts produced, and the decisions made. WorkflowRun is a child of Investigation. Artifact is a child of WorkflowRun.
**Impact on roadmap phases:** Phase 115 (state manager) is the Investigation lifecycle manager. All tracks reference Investigation as the top-level container.
**Verification:** Every COS operation should be traceable to an Investigation ID.
**Revisit triggers:** If the system needs to support work that doesn't map to a question/investigation model.

---

### ADR-004: Build Style
**Date:** 2026-03-27
**Context:** Need to decide monorepo vs multi-repo, packages vs services.
**Decision:** Monorepo with service directories: `cos/core/`, `cos/memory/`, `cos/reasoning/`, etc.
**Options considered:** (A) Single monorepo flat, (B) Multi-repo (like 100-phase series), (C) Monorepo with service dirs
**Tradeoffs:** Monorepo keeps everything in one place for easy cross-module imports. Service directories maintain logical separation by track. Each track maps to a top-level package: `cos.core`, `cos.memory`, `cos.reasoning`, `cos.workflow`, `cos.decision`, `cos.interface`, `cos.intelligence`, `cos.autonomy`.
**Impact on roadmap phases:** Phase 101 (repo restructure) creates the monorepo layout. All subsequent phases add to this single repo rather than creating standalone repos.
**Verification:** `from cos.core import config` works from any module. `python -m cos.core.cli` runs the core CLI.
**Revisit triggers:** If the repo becomes unwieldy (>500 files) or if team collaboration requires separate repos.

---

### ADR-005: Evaluation Framework
**Date:** 2026-03-27
**Context:** Need a minimal benchmark to tell us the system is improving.
**Decision:** Three-metric evaluation: Quality (40%), Cost (40%), Latency (20%).
**Options considered:** Quality-only, Cost-only, balanced tri-metric
**Tradeoffs:** Quality and cost are equally weighted because the COS must produce correct outputs AND be economically viable. Latency is secondary (20%) — the system should be fast enough but correctness and cost matter more.
**Impact on roadmap phases:** Phase 160 (reasoning benchmark suite) and Phase 180 (workflow benchmarking) must implement this tri-metric framework. Every phase that touches evaluation should report quality, cost, and latency.
**Verification:** Each benchmark run produces a score card: `{quality: 0-1, cost_per_investigation: $X, latency_p95: Ns}`.
**Revisit triggers:** If latency becomes a user experience blocker, increase its weight.
