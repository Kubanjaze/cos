# COS — Cognitive Operating System: Implementation Overview

**Version:** 0.1.1 | **Date:** 2026-03-29

## What is COS?
A unified system that ingests information, constructs structured memory, reasons across it, and produces decisions + executable workflows — without manual orchestration.

## Architecture Decisions
| ADR | Decision | Date |
|---|---|---|
| ADR-001 | Local-first CLI toolkit (API-ready interfaces for later) | 2026-03-27 |
| ADR-002 | SQLite + filesystem (cloud migration deferred) | 2026-03-27 |
| ADR-003 | Investigation is the primary unit of work | 2026-03-27 |
| ADR-004 | Monorepo with service directories: `cos/{core,memory,reasoning,...}` | 2026-03-27 |
| ADR-005 | Evaluation: Quality 40% + Cost 40% + Latency 20% | 2026-03-27 |

## Package Structure
```
cos/
├── cos/
│   ├── core/          Track A — infrastructure, config, logging, cost tracking
│   ├── memory/        Track B — document store, embeddings, knowledge graph
│   ├── reasoning/     Track C — synthesis, ranking, hypothesis, uncertainty
│   ├── workflow/      Track D — pipeline definition, execution, scheduling
│   ├── decision/      Track E — action generation, risk assessment, tracking
│   ├── interface/     Track F — UI, chat, dashboards
│   ├── intelligence/  Track G — multi-agent, simulation, meta-reasoning
│   └── autonomy/      Track H — self-scheduling, cost optimization
├── docs/phases/       Per-phase implementation.md + phase_log.md
├── tests/
└── pyproject.toml
```

## Roadmap Progress
See `phases/ROADMAP_COS.md` for the full 120-phase roadmap (101–220).

## Completion Gates
- **Gate 1 (~Phase 106):** ingest → normalize → store → tag → retrieve ✅ PASSED
- **Gate 2 (~Phase 114-116):** register + run pipeline → version outputs → logs
- **Gate 3 (~Phase 132/146/171):** one investigation → ranked outputs + confidence + cost
- **Gate 4 (~Phase 205):** minimal UI can browse + rerun + view artifacts

## Phase History
| Phase | Title | Status |
|---|---|---|
| 101 | Unified project repo restructure | ✅ Complete |
| 102 | Central config system | ✅ Complete |
| 103 | Logging + tracing layer | ✅ Complete |
| 104 | Token + cost tracking middleware | ✅ Complete |
| 105 | File ingestion service (PDF, CSV, TXT) | ✅ Complete |
| 106 | Metadata tagging system | ✅ Complete — **GATE 1 COMPLETE** |
| 107 | Async task queue (background jobs) | ✅ Complete |
| 108 | Storage abstraction (local → cloud-ready) | ✅ Complete |
| 109 | Versioning system for outputs + runs | ✅ Complete |
| 110 | CLI → service transition (command registry) | ✅ Complete |
