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

## 2026-06-04 — Inheritance concentration exponent fix
- **Problem**: Inheritance `inheritance_concentration` parameter equalized wealth instead of concentrating it. Rich workers were net losers because `wealth^conc` with conc<1 gives them less than their linear contribution.
- **Cause**: Used `wealth^conc` as receipt weight. Since conc ∈ [0,1], wealthy contributed linearly (weight=wealth) but received sub-linearly (weight=wealth^conc), making inheritance a net transfer from rich to poor.
- **Solution**: Changed receipt exponent from `conc` to `1 + 2*conc`. At conc=0.5: weight=wealth^2 (quadratic → concentrated). At conc=1.0: weight=wealth^3 (cubic → ~60% to top 10%).
- **Prevention**: Test directionality: with conc>0, top decile should receive more than they contribute. Check top10% receipt share in logs.

## 2026-06-04 — education_variance is the primary Gini driver
- **Problem**: US Gini stuck at 0.32 despite power-law wealth, immigrant wedge, and inheritance all active.
- **Cause**: `education_variance` defaulted to 0 in PHASE8_DEFAULTS. Without education-based wage dispersion, wage distribution is near-uniform regardless of other mechanisms.
- **Solution**: Added `education_variance` (US=0.7, SG=0.5, LF=0.8, etc.) and `wage_dispersion_mult` to every SECTORAL override.
- **Prevention**: Always include `education_variance` when setting up system-level inequality. It's the primary pre-fiscal wage dispersion driver.

## 2026-06-04 — SECTORAL must include all active mechanisms
- **Problem**: Singapore CPF externalities and US skill premium didn't fire because they were only in test SYS dicts, not in SECTORAL.
- **Cause**: SECTORAL was treated as "just sectoral params" but is actually the mechanism-enabling dict for all systems in PHASE8_CONFIGS.
- **Solution**: Expanded SECTORAL to include ALL active mechanisms: CPF externalities, power-law wealth, immigrant wedge, inheritance, structural gap, education_variance.
- **Prevention**: When adding a mech, put it in SECTORAL for the relevant system, not just in a test script. SECTORAL is the single source of truth for per-system config.

## 2026-06-04 — Power-law wealth and structural gap mechanisms added
- **Problem**: Missing causal drivers for US Gini (0.49) and Singapore Gini (0.46) despite existing proxy parameters.
- **Cause**: The existing `super_wealthy_multiplier` is a static scalar that can't produce endogenous return differentials or persistent group-level disparities.
- **Solution**: Added 4 new config-driven mechanisms to `missing_mechanisms.py`: `apply_power_law_wealth` (return premium scaling with log-wealth), `apply_immigrant_wedge` (wage suppression for bottom share), `apply_inheritance_conc` (wealth-weighted bequests), `apply_structural_gap` (group-level wealth multipliers).
- **Prevention**: All default OFF. Backward compatible with existing super_wealthy/inherit_bequest keys.

## 2026-06-05 — Power-law wealth: removed sys-dependency, mechanisms now create wealth
- **Problem**: `apply_power_law_wealth` was zero-effect because it depended on `bal['sys']` having sufficient balance to pay the premium. After ~30 steps, `sys` was drained and the mechanism stopped producing any premium.
- **Cause**: The premium was modeled as a TRANSFER from `sys` to the wealthy tail worker. In reality, higher capital returns are wealth-creating (dividends, capital gains), not pool-redistributing. The `sys` pool model drained the system account, killing the mechanism.
- **Solution**: Changed `if premium > 0 and bal.get('sys', 0) >= premium:` to just `if premium > 0:` — the premium creates new wealth, modeling real capital market returns.
- **Prevention**: Mechanisms that model investment returns should create wealth, not transfer from a system pool. Only transfer-based mechanisms (inheritance, taxation) should debit a source account.

## 2026-06-05 — Power-law premium formula: incorrect 1/12 annualization factor
- **Problem**: `apply_power_law_wealth` had an annual trigger (`step % 12 != 1: return {}`) but still divided the premium by 12: `premium = wealth * premium_rate * (1.0 / 12)`. This made the premium 1/12th of the intended annual return gap.
- **Cause**: The `(1.0/12)` factor was a legacy from an earlier design where the mechanism ran every step. After the trigger was gated to run annually, the factor was never removed.
- **Solution**: Removed the `(1.0 / 12)` factor. Now `premium = wealth * min(0.05, exponent * log_excess)` gives the correct annual return differential.
- **Prevention**: When changing mechanism timing (step → annual), verify all scaling factors are updated. The annualization factor and the trigger gate must be consistent.

## 2026-06-05 — Power-law premium rate cap: explosive compounding at exponent > 0.20
- **Problem**: With the scaling fix, `power_law_exponent=0.25` caused a phase transition — tail wealth exploded to $34M/worker (15x baseline) with Gini 0.96. The uncompounded return gap at 25% premium per log-wealth produces compounding that overwhelms a 20-year simulation.
- **Cause**: The original cap was 0.50 (50pp return premium), far above the empirical 5pp gap (Fagereng et al. 2020: top 1% earn ~10%, median ~5%, gap=5pp).
- **Solution**: Changed cap from `min(0.5, ...)` to `min(0.05, ...)` — 5 percentage points maximum return differential. This produces realistic wealth concentrations without explosive growth.
- **Prevention**: Mechanism caps should be grounded in empirical literature, not chosen as "reasonable" values. The 5pp return gap is a documented empirical regularity.

## 2026-06-05 — Calibrated SECTORAL for US and Singapore mechanism parameters
- **Problem**: The 4 new mechanisms (power-law, immigrant, inheritance, structural gap) were configured with aggressive defaults that overshot real Gini targets: US 0.74 (target 0.49), Singapore 0.61 (target 0.46).
- **Cause**: The initial SECTORAL parameters were chosen before the mechanism bugs were fixed, and represented "high" settings for demonstration.
- **Solution**: After fixing the 3 mechanism bugs, calibrated via parameter sweeps:
  - US: power_law_exponent=0.10, immigrant_share=0.05, inheritance_flow=0.01/conc=0.15, structural_gap_multipliers=[1.0, 0.5]
  - Singapore: inheritance_flow=0.014/conc=0.78 (CPF ext on, immigrant off)
- **Prevention**: Always calibrate after fixing mechanism bugs. Parameters chosen before a bug fix are invalid.

