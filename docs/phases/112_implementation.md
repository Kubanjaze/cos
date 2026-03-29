# Phase 112 — Input Validation Layer

**Version:** 1.1 | **Tier:** Micro | **Date:** 2026-03-29

## Goal
Reusable input validation at system boundaries. Validates file paths, SMILES, investigation IDs, and generic strings. Uses Phase 111 ValidationError for failures.

CLI: No new CLI — integrated into existing modules

Outputs: `cos/core/validation.py` — validation functions

## Logic
1. `validate_file_path(path)` — checks existence, readability, extension in whitelist
2. `validate_smiles(smiles)` — RDKit validation (optional fallback to char-set check)
3. `validate_investigation_id(id)` — alphanumeric + hyphens/underscores/dots, max 128 chars
4. `validate_not_empty(value, field_name)` — generic empty string check
5. `validate_positive_number(value, field_name)` — numeric positivity check
6. All raise `ValidationError` from Phase 111 error hierarchy

## Key Concepts
- **Boundary validation**: validate at entry points, trust internals
- **ValidationError integration**: Phase 111 error hierarchy, classified as PermanentError (no retry)
- **RDKit-optional SMILES**: uses RDKit MolFromSmiles if available, char-set fallback otherwise
- **Whitelist extensions**: .txt, .csv, .pdf, .md, .json, .tsv, .toml, .py, .yaml, .yml
- **Format enforcement**: investigation IDs restricted to `[a-zA-Z0-9_\-\.]`, max 128 chars

## Deviations from Plan
- Added .toml, .py, .yaml, .yml to supported extensions (pyproject.toml needed validation)
- Removed @validated decorator — over-engineering for v0; direct function calls sufficient

## Verification Checklist
- [x] valid file path passes (pyproject.toml)
- [x] missing file raises ValidationError
- [x] valid investigation ID passes (inv-001)
- [x] invalid ID raises (spaces, special chars)
- [x] empty ID raises
- [x] valid SMILES passes (CCO with RDKit)
- [x] invalid SMILES raises
- [x] empty string raises for validate_not_empty

## Risks (resolved)
- RDKit optional: fallback char-set check prevents hard dependency
- Extension whitelist: expanded to include project files (.toml, .py)
- Over-validation: kept minimal — 5 validators, all at boundaries

## Results
| Metric | Value |
|--------|-------|
| Validators | 5 (file_path, smiles, investigation_id, not_empty, positive_number) |
| Tests passed | 8/8 |
| Supported extensions | 10 |
| External deps | 0 (RDKit optional) |
| Cost | $0.00 |

Key finding: RDKit SMILES validation catches invalid molecules that basic regex would miss. The fallback char-set check is a safety net when RDKit isn't installed, but the full validation is preferred.
