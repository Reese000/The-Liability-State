## 2026-06-04 — 10 missing mechanisms implemented (missing_mechanisms.py)
- **Problem**: The simulation was missing 10 mechanisms that would bring it closer to reality — forced savings externalities (CPF liquidity trap/demand suppression/housing feedback), government services productivity, public goods funding requirement, inflation, bankruptcy, endogenous TFP/R&D growth, wage competition, capital ownership distribution, occupational mobility, and overlapping generations.
- **Cause**: The Phase 8 comparison runner had 19 mechanisms for inequality drivers (SBTC, union coverage, import competition, etc.) but none of the structural dynamics that differentiate real economic systems.
- **Solution**: Created `missing_mechanisms.py` (628 lines) with all 10 mechanisms as config-driven functions, wired into `comparison_phase8.py`'s step loop. Each mechanism:
  - Is default OFF (zero-bias baseline preserved)
  - Has its own config key in PHASE8_DEFAULTS
  - Operates on dict balances (no LedgerEngine coupling)
  - Initializes baseline values on first call to prevent compounding bugs
- **Prevention**: Key lessons from implementation: (1) annualize wage-modifying mechanisms (apply once per 12 steps) to prevent compounding explosions, (2) use `_base_hourly` pattern for baseline wage tracking, (3) pass `total_tax` through step_metrics for mechanisms that need tax revenue data.

## 2026-06-04 — Full comparison with mechanisms reshuffles bottom of ranking
- **Problem**: With all 10 mechanisms enabled, Laissez_Faire collapsed from #6 ($1.83M) to #11 ($0.78M) due to public goods requirement. Singapore dropped 10% ($2.30M → $2.06M) from forced savings externalities + inflation.
- **Finding**: The LS cluster is robust — all LVT systems within $1.68-1.70M even with all mechanisms. Laissez_Faire's collapse is the most consequential change. Singapore remains #1 but the gap narrows.
