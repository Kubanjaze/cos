"""COS central configuration system.

Layered config: defaults → cos.toml → .env → environment variables (last wins).
All modules import: `from cos.core.config import settings`
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


def _load_env_file(path: Path) -> dict:
    """Load a .env file into a dict (simple key=value parser)."""
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def _load_toml_file(path: Path) -> dict:
    """Load a cos.toml config file."""
    if not path.exists():
        return {}
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return {}
    return tomllib.loads(path.read_text())


@dataclass
class Settings:
    """COS configuration — single source of truth for all modules."""

    # Storage (ADR-002: SQLite + filesystem)
    storage_dir: str = ""
    db_name: str = "cos.db"

    # API (ADR-001: local-first, API-ready)
    anthropic_api_key: str = ""
    default_model: str = "claude-haiku-4-5-20251001"

    # Logging
    log_level: str = "INFO"
    log_dir: str = ""

    # Cost (ADR-005: 40% weight)
    cost_budget_per_investigation: float = 1.0  # dollars
    cost_warning_threshold: float = 0.8  # fraction of budget

    # Evaluation (ADR-005: quality 40%, cost 40%, latency 20%)
    eval_quality_weight: float = 0.4
    eval_cost_weight: float = 0.4
    eval_latency_weight: float = 0.2

    @property
    def db_path(self) -> str:
        return os.path.join(self.storage_dir, self.db_name)

    @property
    def storage_path(self) -> Path:
        return Path(self.storage_dir)

    def validate(self) -> list[str]:
        """Return list of validation errors (empty = valid)."""
        errors = []
        if not self.storage_dir:
            errors.append("storage_dir is not set")
        if not os.path.isdir(self.storage_dir):
            errors.append(f"storage_dir does not exist: {self.storage_dir}")
        weights = self.eval_quality_weight + self.eval_cost_weight + self.eval_latency_weight
        if abs(weights - 1.0) > 0.01:
            errors.append(f"eval weights must sum to 1.0, got {weights}")
        return errors

    def show(self) -> str:
        """Return human-readable config summary."""
        lines = ["COS Configuration", "=" * 40]
        for key in [
            "storage_dir", "db_name", "db_path", "default_model", "log_level",
            "log_dir", "cost_budget_per_investigation", "cost_warning_threshold",
            "eval_quality_weight", "eval_cost_weight", "eval_latency_weight",
        ]:
            val = getattr(self, key)
            if key == "anthropic_api_key":
                val = val[:8] + "..." if val else "(not set)"
            lines.append(f"  {key}: {val}")
        # API key shown separately (masked)
        api = self.anthropic_api_key
        lines.append(f"  anthropic_api_key: {api[:8] + '...' if api else '(not set)'}")
        return "\n".join(lines)


def load_settings(
    config_file: Optional[str] = None,
    env_file: Optional[str] = None,
) -> Settings:
    """Load settings with layered precedence: defaults → toml → .env → env vars."""

    s = Settings()

    # Default storage dir
    default_storage = os.path.join(Path.home(), ".cos")
    os.makedirs(default_storage, exist_ok=True)
    s.storage_dir = default_storage
    s.log_dir = os.path.join(default_storage, "logs")

    # Layer 1: TOML config file
    toml_path = Path(config_file) if config_file else Path("cos.toml")
    toml = _load_toml_file(toml_path)
    for key, value in toml.items():
        if hasattr(s, key):
            setattr(s, key, value)

    # Layer 2: .env file
    env_path = Path(env_file) if env_file else Path(".env")
    env_vars = _load_env_file(env_path)
    for key, value in env_vars.items():
        attr = key.lower()
        if attr.startswith("cos_"):
            attr = attr[4:]  # strip COS_ prefix
        if hasattr(s, attr):
            # Type coerce
            current = getattr(s, attr)
            if isinstance(current, float):
                setattr(s, attr, float(value))
            elif isinstance(current, int):
                setattr(s, attr, int(value))
            else:
                setattr(s, attr, value)

    # Layer 3: Environment variables (COS_ prefix)
    for key, value in os.environ.items():
        if key.startswith("COS_"):
            attr = key[4:].lower()
            if hasattr(s, attr):
                current = getattr(s, attr)
                if isinstance(current, float):
                    setattr(s, attr, float(value))
                elif isinstance(current, int):
                    setattr(s, attr, int(value))
                else:
                    setattr(s, attr, value)

    # Also pick up ANTHROPIC_API_KEY directly
    if not s.anthropic_api_key and os.environ.get("ANTHROPIC_API_KEY"):
        s.anthropic_api_key = os.environ["ANTHROPIC_API_KEY"]

    return s


# Singleton — import this everywhere
settings = load_settings()
