"""
config.py — Simulation configuration loader
"""
import yaml
from pathlib import Path

DEFAULT_CONFIG = {
    'simulation': {
        'steps': 100,
        'seed': 42,
        'log_level': 'INFO',
    },
    'agents': {
        'population': 50,
        'initial_cash_range': [1000, 10000],
        'honesty_mean': 0.7,
        'honesty_std': 0.15,
        'inertia': 0.1,
    },
    'lvt': {
        'rate': 0.05,
        'alliance_skim': 0.10,
    },
    'insurance': {
        'base_premium_rate': 0.05,
        'min_solvency': 0.1,
        'audit_probability': 0.1,
    },
    'courts': {
        'filing_fee_rate': 0.03,
        'evidence_threshold': 0.2,
        'speed_base': 5,
    },
    'harberger': {
        'bond_fraction': 1.0,
        'penalty_rate': 0.15,
        'free_window_days': 14,
        'bid_expiry_days': 104,
    },
}


def load_config(path: str = None) -> dict:
    """Load config from YAML file, merging with defaults."""
    config = DEFAULT_CONFIG.copy()
    if path and Path(path).exists():
        with open(path) as f:
            user_config = yaml.safe_load(f)
        if user_config:
            _deep_merge(config, user_config)
    return config


def _deep_merge(base, override):
    """Recursively merge override into base."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def save_config(config: dict, path: str):
    """Save config to YAML file."""
    with open(path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
