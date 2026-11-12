"""YAML config loader for the voice recording pipeline.

Loads config.yaml from the tool directory, expands ~ paths,
merges defaults with user overrides, and validates required fields.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)

# Default config file location: same directory as this module
_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(_CONFIG_DIR, "config.yaml")


def _expand_paths(obj: Any) -> Any:
    """Recursively expand ~ in string values that look like paths."""
    if isinstance(obj, str):
        if obj.startswith("~"):
            return os.path.expanduser(obj)
        return obj
    if isinstance(obj, dict):
        return {k: _expand_paths(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_paths(item) for item in obj]
    return obj


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep-merge override into base (override wins on conflicts)."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _validate(cfg: dict) -> None:
    """Validate that required configuration sections exist."""
    required_sections = ["sources", "denoiser", "transcriber", "categorizer", "output", "database"]
    missing = [s for s in required_sections if s not in cfg]
    if missing:
        raise ValueError(f"Missing required config sections: {', '.join(missing)}")

    # Validate sources have at least one enabled
    sources = cfg.get("sources", {})
    if not any(s.get("enabled", False) for s in sources.values()):
        raise ValueError("At least one source must be enabled in config")

    # Validate output base_path is set
    output = cfg.get("output", {})
    if not output.get("base_path"):
        raise ValueError("output.base_path must be set in config")

    # Validate categorizer has categories
    categorizer = cfg.get("categorizer", {})
    if not categorizer.get("categories"):
        raise ValueError("categorizer.categories must be defined in config")


def load_config(
    config_path: Optional[str] = None,
    override: Optional[Dict] = None,
) -> dict:
    """Load and return the pipeline configuration.

    Args:
        config_path: Path to config YAML file. Defaults to config.yaml in tool dir.
        override: Optional dict to deep-merge on top of loaded config.

    Returns:
        Fully resolved configuration dict with expanded paths.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If required config sections are missing.
    """
    path = config_path or DEFAULT_CONFIG_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r") as f:
        cfg = yaml.safe_load(f)

    if cfg is None:
        cfg = {}

    # Apply user overrides
    if override:
        cfg = _deep_merge(cfg, override)

    # Expand ~ in all path-like strings
    cfg = _expand_paths(cfg)

    # Validate
    _validate(cfg)

    # Ensure cache directories exist
    db_path = cfg.get("database", {}).get("path", "")
    if db_path:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    log_path = cfg.get("logging", {}).get("path", "")
    if log_path:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

    denoised_dir = cfg.get("denoiser", {}).get("output_dir", "")
    if denoised_dir:
        os.makedirs(denoised_dir, exist_ok=True)

    logger.debug("Config loaded from %s", path)
    return cfg
