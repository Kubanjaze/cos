# COS Product Roadmap — User Personas & Tailored Development

**Date:** 2026-03-31 | **Version:** 1.0

---

## Target Users

### Persona 1: Computational Chemist / Cheminformatician
**Role:** Analyzes structure-activity relationships, builds QSAR models, prioritizes compound libraries.

**What COS already does for them:**
- SAR analysis page with scaffold profiles, activity heatmaps, head-to-head comparisons
- Knowledge graph showing compound → scaffold → activity relationships
- Hypothesis generation from scaffold-activity patterns
- Pattern detection across 6 scaffold families

**What's missing (build next):**

| Priority | Feature | Effort | Impact |
|----------|---------|--------|--------|
| P0 | **RDKit molecular viewer** — render 2D structures inline from SMILES | 2 days | Compounds are names right now, not structures |
| P0 | **Fingerprint similarity search** — "find compounds similar to benz_001_F" | 1 day | Core workflow: similarity-based SAR |
| P1 | **Matched molecular pair (MMP) analysis** — auto-detect transformations that improve potency | 3 days | This is how med chem thinks |
| P1 | **QSAR model integration** — train RF/XGBoost on COS data, predict new compound activity | 2 days | You built this in Phases 35-54 already |
| P2 | **Scaffold hopping suggestions** — "what if we replace benz core with ind?" | 2 days | Drives compound design |
| P2 | **R-group decomposition view** — break compounds into core + substituents | 2 days | Standard SAR visualization |

---

### Persona 2: Medicinal Chemist
**Role:** Designs and synthesizes new compounds. Decides what to make next.

**What COS already does for them:**
- Decision engine with risk assessment and action prioritization
- "Which scaffold should we prioritize?" answered with data citations
- Tradeoff analysis between scaffold options
- Hypothesis cards showing scaffold-dependent SAR trends

**What's missing (build next):**

| Priority | Feature | Effort | Impact |
|----------|---------|--------|--------|
| P0 | **"What to make next" recommender** — suggest specific substituent changes based on SAR trends | 3 days | The #1 question med chemists ask |
| P0 | **Activity cliff detector** — find pairs where small structural change = big potency change | 2 days | Critical for avoiding bad designs |
| P1 | **Synthetic feasibility scorer** — flag compounds that are hard to make | 2 days | Saves wet lab time |
| P1 | **Compound request tracker** — log "I want to test X" → track through synthesis → results | 2 days | Closes the design-make-test loop |
| P2 | **Patent landscape overlay** — flag scaffolds near existing IP | 3 days | Real-world constraint |

---

### Persona 3: Biology / Pharmacology Lead
**Role:** Runs assays, validates targets, interprets biological data.

**What COS already does for them:**
- Entity extraction (targets: CETP, KRAS, BRAF)
- Concept definitions with confidence scores
- Multi-source synthesis across documents
- Knowledge gap detection

**What's missing (build next):**

| Priority | Feature | Effort | Impact |
|----------|---------|--------|--------|
| P0 | **Assay data import** — ingest IC50/EC50 dose-response data directly | 2 days | Their primary data source |
| P0 | **Target profile page** — one page per target showing all compounds, assays, literature | 2 days | How biologists think |
| P1 | **Selectivity analysis** — compare activity across multiple targets | 2 days | Key for safety |
| P1 | **Literature ingestion** — PDF paper → extract findings → link to entities | 3 days | Phase 105 handles PDF, but needs smarter extraction |
| P2 | **Pathway context** — show where target sits in biological pathway | 3 days | STRING/Reactome integration |

---

### Persona 4: Project Team Lead / Program Manager
**Role:** Oversees drug discovery program. Reports to leadership. Tracks milestones.

**What COS already does for them:**
- Investigation dashboard with counts, health, notifications
- Decision board with risk/action tracking
- Workflow analytics with success rates
- Report generation (JSON export)
- Autonomous investigation runner

**What's missing (build next):**

| Priority | Feature | Effort | Impact |
|----------|---------|--------|--------|
| P0 | **PDF/PowerPoint report export** — one-click presentation-ready output | 2 days | They present to leadership weekly |
| P0 | **Program timeline** — visual Gantt-like view of investigation milestones | 2 days | Program tracking |
| P1 | **Multi-investigation comparison** — compare progress across targets | 1 day | Portfolio view |
| P1 | **Collaboration notes** — team members annotate decisions with comments | 2 days | Team communication |
| P2 | **Email/Slack notifications** — alert on conflicts, new results, deadline risks | 2 days | Stay informed without checking dashboard |

---

### Persona 5: Data Scientist in Drug Discovery
**Role:** Builds ML pipelines, integrates heterogeneous data, queries knowledge graphs.

**What COS already does for them:**
- 40-table SQLite knowledge base with full provenance
- Knowledge graph with BFS traversal, subgraphs, components
- Hybrid search (vector + keyword + graph)
- Memory scoring, pruning, snapshots
- 56-route REST API with Swagger docs at /docs

**What's missing (build next):**

| Priority | Feature | Effort | Impact |
|----------|---------|--------|--------|
| P0 | **Python SDK** — `from cos import COS; cos.search("CETP")` instead of HTTP calls | 2 days | Their natural interface |
| P0 | **Jupyter notebook integration** — COS widgets in notebooks | 2 days | Where they live |
| P1 | **Bulk data export** — dump knowledge graph as NetworkX/CSV/Parquet | 1 day | Feed into their ML pipelines |
| P1 | **Custom embedding models** — swap MiniLM for domain-specific BioBERT | 2 days | Better biomedical retrieval |
| P2 | **MLflow integration** — track model experiments linked to investigations | 3 days | Standard ML workflow |

---

### Persona 6: Academic Researcher / PhD Student
**Role:** Explores new targets, mines literature, generates hypotheses for grant proposals.

**What COS already does for them:**
- Chat interface with AI-powered analysis
- Hypothesis generation from data patterns
- Disconfirmation engine to challenge hypotheses
- Knowledge gap detection ("what don't we know?")

**What's missing (build next):**

| Priority | Feature | Effort | Impact |
|----------|---------|--------|--------|
| P0 | **PubMed/arXiv ingestion** — paste a DOI, COS extracts and links findings | 3 days | How research starts |
| P0 | **Citation graph** — which findings support/contradict which hypotheses | 2 days | Literature review automation |
| P1 | **Grant writing assistant** — AI generates significance/innovation sections from COS knowledge | 2 days | High value, low effort |
| P1 | **Collaboration sharing** — export investigation as portable file, import on another machine | 2 days | Share with lab mates |
| P2 | **Teaching mode** — step-by-step explanations of SAR concepts for students | 1 day | Educational use |

---

## Recommended Build Order (Next 4 Sprints)

### Sprint 1: "Make it visual" (1 week)
**Persona focus:** Computational Chemist + Medicinal Chemist

| Feature | Files to modify |
|---------|----------------|
| RDKit 2D structure rendering in compound tables | `cos/api/routes/sar.py`, `index.html` |
| Activity cliff detection | `cos/reasoning/patterns.py` |
| Fingerprint similarity search | `cos/memory/` new module |
| Better heatmap (compounds as rows, properties as columns) | `index.html` |

### Sprint 2: "Make it smart" (1 week)
**Persona focus:** Biology Lead + Med Chem

| Feature | Files to modify |
|---------|----------------|
| Target profile page (one page per target) | new API route + frontend page |
| Assay data import (CSV with IC50 columns) | `cos/core/ingestion.py` enhancement |
| "What to make next" recommender | `cos/decision/actions.py` enhancement |
| PDF paper ingestion with smarter extraction | `cos/memory/entities.py` enhancement |

### Sprint 3: "Make it shareable" (1 week)
**Persona focus:** Project Lead + Academic

| Feature | Files to modify |
|---------|----------------|
| PDF report export (WeasyPrint or reportlab) | new `cos/api/routes/export.py` |
| Program timeline view | new frontend component |
| PubMed DOI ingestion | new `cos/memory/pubmed.py` |
| Multi-investigation comparison dashboard | frontend enhancement |

### Sprint 4: "Make it extensible" (1 week)
**Persona focus:** Data Scientist

| Feature | Files to modify |
|---------|----------------|
| Python SDK (`pip install cos-sdk`) | new `cos/sdk/` package |
| Jupyter widget | new `cos/sdk/jupyter.py` |
| Bulk export (CSV/Parquet/NetworkX) | new API routes |
| Custom embedding model support | `cos/memory/embeddings.py` enhancement |

---

## Success Metrics per Persona

| Persona | Key Metric | Target |
|---------|-----------|--------|
| Comp Chem | Time to generate SAR report | < 5 minutes (vs hours manually) |
| Med Chem | Compound design suggestions accepted | > 50% hit rate |
| Biology Lead | Literature findings linked to entities | > 80% auto-linked |
| Project Lead | Report generation time | < 30 seconds |
| Data Scientist | API query response time | < 100ms for 95% of queries |
| Academic | Hypothesis generation from new paper | < 2 minutes from DOI to hypotheses |
