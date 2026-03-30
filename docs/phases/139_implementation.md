# Phase 139 — Knowledge Gap Detection

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-30

## Goal
Detect gaps and weaknesses in the memory system's knowledge coverage. Identifies unlinked entities, low-confidence items, orphan chunks, missing provenance, and sparse domains to guide targeted data acquisition.

CLI: `python -m cos gaps {detect,summary}`

Outputs: No new DB table — queries existing tables to identify gaps.

## Logic
1. `GapDetector` class in `cos/memory/gaps.py` with methods: `detect_all`, `find_unlinked_entities`, `find_low_confidence`, `find_orphan_chunks`, `find_missing_provenance`, `find_sparse_domains`, `summary`
2. `find_unlinked_entities` identifies entities with no relations or cross-domain links
3. `find_low_confidence` flags memory items below a confidence threshold
4. `find_orphan_chunks` finds ingested chunks not linked to any entity
5. `find_missing_provenance` detects items without provenance records
6. `find_sparse_domains` identifies domains with very few items
7. `detect_all` runs all five gap detectors and aggregates results
8. `summary` provides a concise gap report with counts and priorities

## Key Concepts
- **Multi-dimensional gap analysis**: five orthogonal gap types covering connectivity, quality, coverage, provenance, and domain breadth
- **Actionable gaps**: each detected gap suggests a remedy (add relations, re-ingest with provenance, fetch external data)
- **Quality feedback loop**: gap detection drives targeted knowledge acquisition, improving memory completeness over time
- **No new schema**: purely analytical — queries existing tables without modification

## Verification Checklist
- [x] `detect` runs all gap detectors without error
- [x] `summary` shows gap counts by type
- [x] Low-confidence items correctly identified
- [x] Sparse domains correctly identified
- [x] Results are actionable (each gap has a clear remedy)

## Risks (resolved)
- False positives: some "gaps" may be intentional (e.g., entities that genuinely have no relations) — summary includes context for human judgment
- Threshold sensitivity: low-confidence and sparse-domain thresholds are hardcoded but reasonable defaults

## Results
| Metric | Value |
|--------|-------|
| Gaps detected | 2 |
| Gap types | 1 low-confidence concept, 1 sparse domain |
| Gap detectors | 5 (unlinked, low-confidence, orphan, provenance, sparse) |
| New DB tables | 0 |
| External deps | 0 |
| Cost | $0.00 |

Key finding: Two gaps were detected — a low-confidence concept and a sparse domain — demonstrating that the gap detector can surface actionable weaknesses. As memory grows, this becomes the primary tool for guiding targeted knowledge acquisition.
