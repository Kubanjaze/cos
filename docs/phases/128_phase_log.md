# Phase 128 — Procedural Memory Layer

**Status:** 🔄 In Progress
**Started:** 2026-03-30
**Repo:** https://github.com/Kubanjaze/cos

---

## Log

### 2026-03-30 12:35 — Plan written, initial push
- Phase 128: Procedural memory layer (saved workflows)
- Persistent reusable procedures with define-time command validation
- DB table: `procedures` (table 16 in COS)
- CLI: `python -m cos procedures {define,list,get,run,update,delete,stats}`
- Completes 3-kind memory model (episodic + semantic + procedural)
- Incorporates Pisces review feedback: case-insensitive uniqueness, steps schema versioning, define-time validation, execution contract with finally-path counters
