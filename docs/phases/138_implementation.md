# Phase 138 — External Knowledge Connectors

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-03-30

## Goal
Create a connector registry for fetching external knowledge from scientific databases. Provides a pluggable architecture where new data sources can be registered and queried through a uniform interface.

CLI: `python -m cos connectors {list,fetch,stats}`

Outputs: `connector_log` table (DB table 23) recording fetch operations.

## Logic
1. `ConnectorRegistry` class in `cos/memory/connectors.py` with methods: `register`, `fetch`, `list_connectors`, `stats`
2. `register` adds a new connector with name, base_url, and fetch handler
3. `fetch` calls the named connector's handler to retrieve external data
4. `list_connectors` shows all registered connectors with status
5. `stats` reports fetch counts, success/failure rates by connector
6. Three stub connectors pre-registered: ChEMBL, PubChem, UniProt
7. Fetch operations logged in `connector_log` table (DB table 23) with connector_name, query, status, timestamp

## Key Concepts
- **Connector registry pattern**: pluggable architecture for adding new data sources without code changes
- **Stub connectors**: ChEMBL, PubChem, UniProt registered with placeholder fetch handlers
- **Fetch logging**: all external queries recorded for audit and rate-limit tracking
- **DB table 23**: `connector_log` — records every external fetch attempt
- **Foundation for Phases 80-94 integration**: connectors bridge COS memory to external databases studied in the learning series

## Verification Checklist
- [x] `list` shows 3 registered connectors (ChEMBL, PubChem, UniProt)
- [x] `fetch` executes a connector's handler and logs the operation
- [x] `stats` reports fetch counts by connector
- [x] DB table `connector_log` created
- [x] New connectors can be registered dynamically

## Risks (resolved)
- Stub-only connectors: real API integration deferred to future phases — stubs validate the architecture
- Rate limiting: connector_log captures timestamps for future rate-limit enforcement

## Results
| Metric | Value |
|--------|-------|
| Connectors registered | 3 (ChEMBL, PubChem, UniProt) |
| Fetch verified | Yes (stub mode) |
| DB table | connector_log (table 23) |
| External deps | 0 |
| Cost | $0.00 |

Key finding: The connector registry pattern cleanly separates data source registration from fetch logic. Adding a new external database requires only registering a handler function — no changes to the query engine or CLI.
