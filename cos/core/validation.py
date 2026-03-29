"""COS input validation layer.

Validates inputs at system boundaries before they reach business logic.
All validators raise ValidationError (from cos.core.errors) on failure.

Usage:
    from cos.core.validation import validate_file_path, validate_investigation_id, validate_smiles
    validate_file_path("data/compounds.csv")  # raises ValidationError if invalid
"""

import os
import re
from pathlib import Path
from typing import Optional

from cos.core.errors import ValidationError
from cos.core.logging import get_logger

logger = get_logger("cos.core.validation")

SUPPORTED_EXTENSIONS = {".txt", ".csv", ".pdf", ".md", ".json", ".tsv", ".toml", ".py", ".yaml", ".yml"}


def validate_file_path(path: str, must_exist: bool = True) -> Path:
    """Validate a file path. Returns resolved Path on success."""
    if not path or not path.strip():
        raise ValidationError("File path is empty")

    p = Path(path)

    if must_exist and not p.exists():
        raise ValidationError(f"File not found: {path}")

    if must_exist and not p.is_file():
        raise ValidationError(f"Not a file: {path}")

    ext = p.suffix.lower()
    if ext and ext not in SUPPORTED_EXTENSIONS:
        raise ValidationError(f"Unsupported file type: {ext}. Supported: {sorted(SUPPORTED_EXTENSIONS)}")

    return p.resolve()


def validate_investigation_id(investigation_id: str) -> str:
    """Validate investigation ID format. Returns cleaned ID."""
    if not investigation_id or not investigation_id.strip():
        raise ValidationError("Investigation ID is empty")

    cleaned = investigation_id.strip()

    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', cleaned):
        raise ValidationError(
            f"Invalid investigation ID: '{cleaned}'. "
            "Must contain only alphanumeric chars, hyphens, underscores, dots."
        )

    if len(cleaned) > 128:
        raise ValidationError(f"Investigation ID too long: {len(cleaned)} chars (max 128)")

    return cleaned


def validate_smiles(smiles: str) -> str:
    """Validate a SMILES string. Returns cleaned SMILES."""
    if not smiles or not smiles.strip():
        raise ValidationError("SMILES string is empty")

    cleaned = smiles.strip()

    # Try RDKit validation if available
    try:
        from rdkit import Chem
        mol = Chem.MolFromSmiles(cleaned)
        if mol is None:
            raise ValidationError(f"Invalid SMILES (RDKit): {cleaned}")
        return cleaned
    except ImportError:
        pass

    # Fallback: basic format check (no RDKit)
    if len(cleaned) < 1:
        raise ValidationError("SMILES too short")

    # SMILES should contain valid characters
    valid_chars = set("BCNOPSFIHbcnopsfi[]()=#@+\\/-%.0123456789")
    invalid = set(cleaned) - valid_chars
    if invalid:
        raise ValidationError(f"Invalid SMILES characters: {invalid}")

    return cleaned


def validate_not_empty(value: str, field_name: str = "value") -> str:
    """Validate that a string is not empty."""
    if not value or not value.strip():
        raise ValidationError(f"{field_name} is empty")
    return value.strip()


def validate_positive_number(value: float, field_name: str = "value") -> float:
    """Validate that a number is positive."""
    if value <= 0:
        raise ValidationError(f"{field_name} must be positive, got {value}")
    return value
