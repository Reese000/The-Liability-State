#!/usr/bin/env python3
"""
compact_competition_bridge.py — Multi-compact system for tax & court competition.

Splits workers and businesses into multiple "compacts" (jurisdictions) with
different court biases, litigation rates, and LVT modifiers.  Enables tax
competition and forum-shopping for litigation.

Exports
-------
create_compacts(workers, businesses, n_compacts=2, seed=42)
    -> (compacts dict, worker_compact_map, biz_compact_map)

    *workers* and *businesses* are lists of dicts (or objects) each containing
    an ``'id'`` key (or ``.id`` attribute).  Agents are shuffled and split
    round-robin across *n_compacts*.

    Returns
    -------
    compacts : dict[str, dict]
        Mapping compact_id -> compact config dict with keys:
        ``id``, ``name``, ``court_bias``, ``litigation_rate``, ``lvt_modifier``.
    worker_compact_map : dict[str, str]
        Mapping worker_id -> compact_id.
    biz_compact_map : dict[str, str]
        Mapping business_id -> compact_id.

apply_compact_court_bias(court, compact_id, compacts=None)
    -> Court  (modified in-place)

    Adjusts the given Court object's ``bias`` field to reflect the compact's
    ``court_bias`` (mapped from the compact's [0.5, 0.9] range to the Court's
    [-0.2, +0.2] range).

Usage
-----
    from compact_competition_bridge import create_compacts, apply_compact_court_bias

    compacts, wmap, bmap = create_compacts(workers, businesses, n_compacts=3)

    # Assign worker/business compact_id attributes
    for w in workers:
        w['compact_id'] = wmap[w['id']]
    for b in businesses:
        b['compact_id'] = bmap[b['id']]

    # Configure a court for a compact
    court = Court('fast', 'Fast Court', 0.03, 3, 0.7, 0.0)
    apply_compact_court_bias(court, 'compact_0', compacts)
"""

from __future__ import annotations

import logging
import random
from typing import Any, Optional

# ── Logger ───────────────────────────────────────────────────────────
logger = logging.getLogger("compact_competition_bridge")

# ── Module-level compact cache (populated by create_compacts, used by
#    apply_compact_court_bias when no compacts dict is passed). ──────
_COMPACTS_CACHE: dict[str, dict] = {}


# ═══════════════════════════════════════════════════════════════════════
#  Compact Names
# ═══════════════════════════════════════════════════════════════════════

_COMPACT_NAMES = [
    "Alpha", "Beta", "Gamma", "Delta", "Epsilon",
    "Zeta", "Eta", "Theta", "Iota", "Kappa",
    "Lambda", "Mu", "Nu", "Xi", "Omicron",
    "Pi", "Rho", "Sigma", "Tau", "Upsilon",
]


# ═══════════════════════════════════════════════════════════════════════
#  Internal Helpers
# ═══════════════════════════════════════════════════════════════════════

def _get_id(x: Any) -> str:
    """Extract the id from a dict or object."""
    if isinstance(x, dict):
        return x["id"]
    return x.id


def _set_compact_id(x: Any, cid: str) -> None:
    """Set compact_id on a dict or object, creating the attribute if needed."""
    if isinstance(x, dict):
        x["compact_id"] = cid
    else:
        setattr(x, "compact_id", cid)


# ═══════════════════════════════════════════════════════════════════════
#  Core API
# ═══════════════════════════════════════════════════════════════════════

def create_compacts(
    workers: list,
    businesses: list,
    n_compacts: int = 2,
    seed: int = 42,
) -> tuple[dict[str, dict], dict[str, str], dict[str, str]]:
    """
    Split workers and businesses into *n_compacts* jurisdictional groups.

    Each compact receives a randomised:
      - ``court_bias``     ∈ [0.5, 0.9]  — higher = more plaintiff-friendly
      - ``litigation_rate`` ∈ [0.01, 0.03] — per-step suit probability
      - ``lvt_modifier``   ∈ [0.8, 1.2]  — scales the effective LVT rate

    Agents are shuffled (seeded) then assigned round-robin for roughly
    even compact sizes.

    Parameters
    ----------
    workers : list[dict | object]
        Worker agents, each with an ``'id'`` key / ``.id`` attribute.
    businesses : list[dict | object]
        Business agents, each with an ``'id'`` key / ``.id`` attribute.
    n_compacts : int
        Number of compacts to create (default 2).
    seed : int
        RNG seed for reproducibility (default 42).

    Returns
    -------
    (compacts, worker_compact_map, biz_compact_map)
    """
    if n_compacts < 1:
        raise ValueError(f"n_compacts must be >= 1, got {n_compacts}")

    rng = random.Random(seed)

    # ── Generate compact configs ─────────────────────────────────
    compacts: dict[str, dict] = {}
    for i in range(n_compacts):
        cid = f"compact_{i}"
        name = _COMPACT_NAMES[i] if i < len(_COMPACT_NAMES) else f"Compact-{i}"
        compacts[cid] = {
            "id": cid,
            "name": name,
            "court_bias": round(rng.uniform(0.5, 0.9), 3),
            "litigation_rate": round(rng.uniform(0.01, 0.03), 4),
            "lvt_modifier": round(rng.uniform(0.8, 1.2), 3),
        }

    # ── Assign workers to compacts ───────────────────────────────
    worker_ids = [_get_id(w) for w in workers]
    rng.shuffle(worker_ids)
    worker_compact_map: dict[str, str] = {}
    for idx, wid in enumerate(worker_ids):
        cid = f"compact_{idx % n_compacts}"
        worker_compact_map[wid] = cid

    # ── Assign businesses to compacts ────────────────────────────
    biz_ids = [_get_id(b) for b in businesses]
    rng.shuffle(biz_ids)
    biz_compact_map: dict[str, str] = {}
    for idx, bid in enumerate(biz_ids):
        cid = f"compact_{idx % n_compacts}"
        biz_compact_map[bid] = cid

    # ── Update module-level cache ────────────────────────────────
    _COMPACTS_CACHE.clear()
    _COMPACTS_CACHE.update(compacts)

    return compacts, worker_compact_map, biz_compact_map


def get_compact_for_entity(
    entity_id: str,
    worker_compact_map: dict[str, str],
    biz_compact_map: dict[str, str],
) -> Optional[str]:
    """
    Look up the compact_id for a given entity ID.

    Checks the worker map first, then the business map.
    Returns None if not found in either.
    """
    if entity_id in worker_compact_map:
        return worker_compact_map[entity_id]
    if entity_id in biz_compact_map:
        return biz_compact_map[entity_id]
    return None


def apply_compact_court_bias(
    court: Any,
    compact_id: str,
    compacts: Optional[dict[str, dict]] = None,
) -> Any:
    """
    Adjust a Court's bias to reflect a compact's court_bias.

    The compact's ``court_bias`` (range [0.5, 0.9]) is mapped linearly
    to the Court's ``bias`` field (range [-0.2, +0.2]):

        court.bias = (court_bias - 0.5) / 2.0

    So a neutral compact (court_bias=0.5) yields bias=0.0, while a
    strongly plaintiff-friendly compact (court_bias=0.9) yields bias=+0.2.

    Parameters
    ----------
    court : Court
        A ``src.mechanics.courts.Court`` instance.  Modified in-place.
    compact_id : str
        The compact whose bias to apply.
    compacts : dict or None
        The compacts dict from ``create_compacts()``.  If None, falls
        back to the module-level cache (populated by the last call to
        ``create_compacts()``).

    Returns
    -------
    Court
        The same court object with its ``bias`` field updated.
    """
    if compacts is None:
        compacts = _COMPACTS_CACHE

    compact = compacts.get(compact_id)
    if compact is None:
        raise KeyError(
            f"Compact '{compact_id}' not found in compacts dict. "
            f"Available: {list(compacts.keys())}"
        )

    court_bias_raw = compact["court_bias"]  # ∈ [0.5, 0.9]

    # Map [0.5, 0.9] → [-0.2, +0.2]  (Court.bias domain)
    #  0.5 → 0.0  (neutral)
    #  0.7 → 0.1  (slightly pro-plaintiff)
    #  0.9 → 0.2  (max pro-plaintiff)
    mapped_bias = (court_bias_raw - 0.5) / 2.0

    # Clamp to Court's documented range [-0.2, +0.2]
    court.bias = max(-0.2, min(0.2, mapped_bias))

    return court


def get_compact_lvt_modifier(
    compact_id: str,
    compacts: Optional[dict[str, dict]] = None,
) -> float:
    """
    Return the LVT modifier for a compact (scales the base LVT rate).

    Parameters
    ----------
    compact_id : str
        The compact's id.
    compacts : dict or None
        Compacts dict; falls back to module-level cache.

    Returns
    -------
    float
        LVT modifier ∈ [0.8, 1.2].  Multiply the global LVT rate by this
        to get the effective rate for this compact.
    """
    if compacts is None:
        compacts = _COMPACTS_CACHE
    compact = compacts.get(compact_id)
    if compact is None:
        raise KeyError(f"Compact '{compact_id}' not found")
    val = compact["lvt_modifier"]
    if not (0.8 <= val <= 1.2):
        logger.warning(
            "Compact '%s' has lvt_modifier=%.4f, outside expected range [0.8, 1.2]",
            compact_id, val,
        )
    return val


def get_compact_litigation_rate(
    compact_id: str,
    compacts: Optional[dict[str, dict]] = None,
) -> float:
    """
    Return the per-step litigation probability for a compact.

    Parameters
    ----------
    compact_id : str
        The compact's id.
    compacts : dict or None
        Compacts dict; falls back to module-level cache.

    Returns
    -------
    float
        Litigation rate ∈ [0.01, 0.03].
    """
    if compacts is None:
        compacts = _COMPACTS_CACHE
    compact = compacts.get(compact_id)
    if compact is None:
        raise KeyError(f"Compact '{compact_id}' not found")
    val = compact["litigation_rate"]
    if not (0.01 <= val <= 0.03):
        logger.warning(
            "Compact '%s' has litigation_rate=%.4f, outside expected range [0.01, 0.03]",
            compact_id, val,
        )
    return val


def assign_compact_ids(
    workers: list,
    businesses: list,
    worker_compact_map: dict[str, str],
    biz_compact_map: dict[str, str],
) -> None:
    """
    Set ``compact_id`` on every agent in-place.

    For dict agents sets ``agent['compact_id']``; for objects sets
    ``agent.compact_id``.

    Parameters
    ----------
    workers : list[dict | object]
    businesses : list[dict | object]
    worker_compact_map : dict[str, str]
        From ``create_compacts()``.
    biz_compact_map : dict[str, str]
        From ``create_compacts()``.
    """
    for w in workers:
        wid = _get_id(w)
        cid = worker_compact_map.get(wid)
        if cid is not None:
            _set_compact_id(w, cid)

    for b in businesses:
        bid = _get_id(b)
        cid = biz_compact_map.get(bid)
        if cid is not None:
            _set_compact_id(b, cid)


# ═══════════════════════════════════════════════════════════════════════
#  Self-Test / Demonstration
# ═══════════════════════════════════════════════════════════════════════

def demo() -> None:
    """Run a quick demo of compact creation and court bias application."""
    print("═" * 72)
    print("  COMPACT COMPETITION BRIDGE — Demonstration")
    print("═" * 72)

    # ── Create mock agents ───────────────────────────────────────
    workers = [
        {"id": f"w{i:03d}", "hourly": 20.0 + i * 0.5}
        for i in range(10)
    ]
    businesses = [
        {"id": f"b{i:03d}", "capital": 100_000 + i * 10_000}
        for i in range(4)
    ]

    # ── Create compacts ──────────────────────────────────────────
    compacts, wmap, bmap = create_compacts(
        workers, businesses, n_compacts=3, seed=42,
    )

    print(f"\n▶ Created {len(compacts)} compacts:\n")
    for cid, c in compacts.items():
        print(f"  {cid:12s}  name={c['name']:8s}  "
              f"court_bias={c['court_bias']:.3f}  "
              f"litigation_rate={c['litigation_rate']:.4f}  "
              f"lvt_modifier={c['lvt_modifier']:.3f}")

    print(f"\n▶ Worker assignments:\n")
    for wid, cid in sorted(wmap.items()):
        print(f"  {wid} → {cid}")

    print(f"\n▶ Business assignments:\n")
    for bid, cid in sorted(bmap.items()):
        print(f"  {bid} → {cid}")

    # ── Apply compact IDs on agents ──────────────────────────────
    assign_compact_ids(workers, businesses, wmap, bmap)
    print(f"\n▶ After assign_compact_ids:")
    for w in workers:
        print(f"  {w['id']}  compact_id={w.get('compact_id', 'N/A')}")

    # ── Apply compact court bias ─────────────────────────────────
    # Import here so standalone execution doesn't require the full
    # simulation package to be importable.
    try:
        from src.mechanics.courts import Court

        print(f"\n▶ Applying compact court bias:\n")
        for cid in compacts:
            court = Court(
                court_id=f"court_{cid}",
                name=f"{compacts[cid]['name']} Court",
                filing_fee_rate=0.03,
                speed_factor=3.0,
                fairness_factor=0.7,
                bias=0.0,
            )
            original_bias = court.bias
            apply_compact_court_bias(court, cid, compacts)
            raw = compacts[cid]["court_bias"]
            print(f"  {cid:12s}  raw_bias={raw:.3f}  "
                  f"court.bias: {original_bias:+.2f} → {court.bias:+.2f}")

    except ImportError:
        print("\n  (Court class not importable — skipping bias demo)")

    # ── Summary ──────────────────────────────────────────────────
    print(f"\n{'─' * 72}")
    print(f"✅  Demo complete.  {len(workers)} workers, "
          f"{len(businesses)} businesses split across "
          f"{len(compacts)} compacts.")
    print(f"{'─' * 72}")


if __name__ == "__main__":
    demo()
