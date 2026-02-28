import os
from pathlib import Path
from copy import deepcopy

import yaml


CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


def deep_merge(base: dict, override: dict) -> dict:
    """Deep-merge override into base. Override values win for non-dict leaves."""
    result = deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_defaults(config_dir: Path | None = None) -> dict:
    config_dir = config_dir or CONFIG_DIR
    return load_yaml(config_dir / "defaults.yaml")


def load_site_config(site: str, config_dir: Path | None = None) -> dict:
    config_dir = config_dir or CONFIG_DIR
    site_path = config_dir / "sites" / f"{site}.yaml"
    if not site_path.exists():
        raise FileNotFoundError(f"Site config not found: {site_path}")
    return load_yaml(site_path)


def load_merged_config(site: str, config_dir: Path | None = None) -> dict:
    """Load defaults and merge with site-specific config."""
    defaults = load_defaults(config_dir)
    site_config = load_site_config(site, config_dir)
    return deep_merge(defaults, site_config)


def list_sites(config_dir: Path | None = None) -> list[str]:
    config_dir = config_dir or CONFIG_DIR
    sites_dir = config_dir / "sites"
    if not sites_dir.exists():
        return []
    return [p.stem for p in sites_dir.glob("*.yaml")]
