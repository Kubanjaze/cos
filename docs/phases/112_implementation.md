# Phase 112 — Input Validation Layer

**Version:** 1.0 | **Tier:** Micro | **Date:** 2026-03-29

## Goal
Build a reusable input validation layer for COS. Validates file paths, SMILES strings, investigation IDs, and configuration values before they reach business logic. Uses the Phase 111 ValidationError for failures.

CLI: No new CLI — validation integrated into existing commands

Outputs: `cos/core/validation.py` — validation functions importable by all modules

## Logic
1. Create `cos/core/validation.py` with validation functions
2. `validate_file_path(path)` — checks existence, readability, supported extension
3. `validate_smiles(smiles)` — checks with RDKit if available, otherwise basic format check
4. `validate_investigation_id(id)` — format check (alphanumeric + hyphens + underscores)
5. `validate_config(settings)` — runs settings.validate() and raises ValidationError on failure
6. `@validated` decorator — validates function arguments before execution
7. All validators raise `ValidationError` (from Phase 111) on failure

## Key Concepts
- **Boundary validation**: validate at system entry points, trust internal code
- **ValidationError integration**: uses Phase 111 error hierarchy
- **RDKit-optional**: SMILES validation works with or without RDKit installed
- **Decorator pattern**: `@validated` can auto-validate annotated params
- **Fail early**: validation happens before any computation or API calls

## Verification Checklist
- [ ] `validate_file_path("exists.csv")` passes for valid file
- [ ] `validate_file_path("missing.xyz")` raises ValidationError
- [ ] `validate_investigation_id("inv-001")` passes
- [ ] `validate_investigation_id("")` raises ValidationError
- [ ] `validate_smiles("CCO")` passes (valid SMILES)
- [ ] `validate_smiles("not_a_smiles!!!")` raises ValidationError

## Risks
- RDKit dependency for SMILES validation: made optional with fallback
- Over-validation: only validate at boundaries, not between internal modules
- Regex-based ID validation may be too strict or too loose — start permissive
