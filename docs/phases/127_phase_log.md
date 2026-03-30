# Phase 127 — Semantic Memory Layer

**Status:** 🔄 In Progress
**Started:** 2026-03-30
**Repo:** https://github.com/Kubanjaze/cos

---

## Log

### 2026-03-30 12:00 — Plan written, initial push
- Phase 127: Semantic memory layer (concept definitions)
- Stores domain knowledge as structured concepts with confidence + provenance
- DB table: `concepts` (table 15 in COS)
- CLI: `python -m cos concepts {define,list,get,search,update,stats}`
- Follows episodic memory pattern (Phase 126) but for "what we know" vs "what happened"
