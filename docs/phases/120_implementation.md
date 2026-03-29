# Phase 120 — System Health Dashboard (Internal)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-29

## Goal
Aggregated health dashboard showing status from all COS core modules — the "cockpit view." Track A capstone: ties together all 19 prior infrastructure phases.

CLI: `python -m cos health`

Outputs: Formatted health report to console

## Logic
1. `get_health_report()` aggregates from 7 modules: storage, cache, cost, tasks, investigations, ratelimit, config
2. Each module wrapped in try/except — partial report on error
3. `format_health_report()` renders as human-readable text
4. Module status: OK or error message
5. Sections: storage (files + DB), cache (entries + hits), cost (total + events), tasks (by status), investigations (by status), config validation

## Key Concepts
- **Aggregation-only module**: reads from existing modules, adds no new logic/tables
- **Error resilience**: each module check wrapped in try/except
- **All 7 core modules**: storage, cache, cost, tasks, investigations, ratelimit, config
- **Track A capstone**: demonstrates all infrastructure working together
- **Foundation for Phase 205 UI**: this data feeds the future web dashboard

## Verification Checklist
- [x] All 7 modules report OK
- [x] Storage: 6 files, 108,752 bytes, 8 DB tables
- [x] Cache: 0 active entries (expected — no active caching yet)
- [x] Cost: $0.0123 total (3 events from Phase 104 test)
- [x] Tasks: 1 completed (from Phase 107 test)
- [x] Investigations: 1 active (from Phase 115 test)
- [x] Config: Valid
- [x] `python -m cos health` renders clean formatted output
- [x] **TRACK A COMPLETE**: all 20 phases (101-120) built and verified

## Risks (resolved)
- Module import errors: each section in try/except — partial report is better than crash
- Performance: all simple aggregation queries, instantaneous at v0 scale

## Results
| Metric | Value |
|--------|-------|
| Modules monitored | 7 (all OK) |
| Storage | 6 files (108 KB), DB 94 KB, 8 tables |
| Data present | cost ($0.0123), tasks (1), investigations (1) |
| Track A | ✅ COMPLETE (20/20 phases) |
| External deps | 0 |
| Cost | $0.00 |

Key finding: The health dashboard proves Track A works as a system — all 7 core modules interoperate cleanly, data flows between them (investigations link to artifacts, costs, versions), and the cockpit view gives instant visibility. COS is ready for Track B (Memory System).
