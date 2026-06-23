# tasks.md — Implement Missing Inequality Mechanisms

## Strategic Context
Research identified 4 systematic gaps between simulation output and real-world inequality:
- US Gini 0.28 vs 0.49 (−43%)  
- Singapore Gini 0.20 vs 0.46 (−57%)
- Causal drivers: top-end wealth concentration, immigrant labor wedge, inheritance concentration, structural wealth gaps

**Agreed approach:** Add 4 config-driven mechanisms (all default OFF, zero-bias baseline) rather than overloading existing parameters as proxies. Mechanisms must have causal validity — they replicate the actual channels, not just the aggregate moments.

## Execution Plan

### Task 1: Enhanced Wealth Concentration (replace super_wealthy)
- **Files:** `missing_mechanisms.py`
- **Dependencies:** None
- **Steps:**
  1. Replace `apply_super_wealthy` with `apply_power_law_wealth` 
  2. Use config keys: `use_power_law_wealth` (bool), `power_law_exponent` (float, default 0.3 — return premium per log-wealth), `wealth_tail_fraction` (float, default 0.01 — top 1%)
  3. Mechanism: top `wealth_tail_fraction` of workers get a return premium on wealth that scales with their log-wealth (mimicking higher returns for top decile)
  4. Keeps `_super_wealthy` tag for backward compat
- **Verification:** With exponent=0.3, top 1% wealth share > 30% after 30yr

### Task 2: Immigrant Labor Wedge
- **Files:** `missing_mechanisms.py`
- **Dependencies:** None
- **Steps:**
  1. Add `use_immigrant_labor` (bool), `immigrant_share` (float, 0-1), `immigrant_wage_penalty` (float, 0-1)
  2. Bottom `immigrant_share` of workers (by hourly wage) get wages suppressed by `immigrant_wage_penalty` fraction
  3. Works independently of `informal_share` — both can be active
  4. Immigrant workers do not pay income tax (model reality of undocumented/guest worker gap)
- **Verification:** With share=0.3, penalty=0.5 → bottom 30% wages cut in half → Gini rises >0.35

### Task 3: Concentrated Inheritance
- **Files:** `missing_mechanisms.py`
- **Dependencies:** None
- **Steps:**
  1. Replace `inherit_bequest` logic with `inheritance_concentration` param
  2. Config: `inheritance_flow_fraction` (float, 0-1, fraction of wealth redistributed as inheritance per year), `inheritance_concentration` (float, 0-1, 0=equal, 1=wealth-weighted)
  3. Applied at simulation end (post-step), flows proportionally to existing wealth
  4. Replaces flat `inherit_bequest` — old key still supported for backward compat
- **Verification:** With concentration=1.0, top 10% receive >60% of inheritance flow

### Task 4: Structural Wealth Gap
- **Files:** `missing_mechanisms.py`
- **Dependencies:** None
- **Steps:**
  1. Config: `use_structural_gap` (bool), `structural_gap_groups` (list of fractions, e.g., [0.8, 0.2] for majority/minority), `structural_gap_multipliers` (list of wealth multipliers, e.g., [1.0, 0.1])
  2. At step 1, workers are randomly assigned to groups. Group multiplier persists as a wealth penalty/bonus applied at birth (initial cash) and inherited.
  3. Mechanism applies to initial wealth distribution only (not recurring)
- **Verification:** With gap 10:1, group-specific wealth ratio persists >9:1 after 30yr

### Task 5: Update PHASE8_DEFAULTS and SECTORAL
- **Files:** `comparison_phase8.py`
- **Steps:**
  1. Add new default config keys to PHASE8_DEFAULTS (all OFF)
  2. Update SECTORAL overrides:
     - US_Style: power_law_exponent=0.3, immigrant_share=0.15, immigrant_wage_penalty=0.4, inheritance_concentration=0.8
     - Singapore: immigrant_share=0.35, immigrant_wage_penalty=0.5, inheritance_concentration=0.6
     - Laissez_Faire: inheritance_concentration=0.9, power_law_exponent=0.5

### Task 6: Verify Backtests Still Pass (all mechs OFF)
- **Files:** `run_all_backtests.py`
- **Steps:**
  1. Run full backtest suite
  2. All 9/9 must pass with mechanisms OFF
  3. If any fail, fix the mechanism interaction before proceeding

### Task 7: Run Comparison (5 seeds × 10 systems)
- **Files:** `run_final_comparison.py` or new script
- **Steps:**
  1. Run 5 seeds × all 10 systems
  2. Verify US Gini > 0.40, Singapore Gini > 0.35
  3. Print ranking table

## Risk Register
| Risk | Mitigation |
|------|-----------|
| New mechanisms break backtests | All default OFF — backtests run with mechanisms=OFF |
| Power-law exponent too aggressive causing instability | Cap exponent at 0.5, cap wealth share at 50% |
| Immigrant wedge + informal share interaction confusing | Keep them independent — both OFF by default |
| Inheritance concentration blows up Gini | Cap at concentration=1.0 (wealth-weighted, not runaway) |
| Old super_wealthy/inherit_bequest break | Keep backward compat — old keys still work |

## Decision Gate Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-04 | Implement 4 mechanisms rather than tuning existing params | Debate showed proxy approach fails under policy shocks; causal validity requires structural mechanisms |
| 2026-06-04 | Replace super_wealthy with power_law_wealth | Existing multiplier can't produce 30%+ top 1% share; return differential is documented empirical fact |
| 2026-06-04 | Replace inherit_bequest with inheritance_concentration | Old mechanism redistributed equally; real inheritance concentrates to wealthy |
| 2026-06-04 | Keep immigrant_wedge separate from informal_share | Both are real-world channels with different policy implications; conflation would bias counterfactuals |

## Completed Items
| Date | Task | Status |
|------|------|--------|
| 2026-06-04-05 | Implement 4 missing inequality mechanisms (power_law_wealth, immigrant_wedge, inheritance_conc, structural_gap) in `missing_mechanisms.py` | ✅ Done |
| 2026-06-05 | Wire mechanisms into `comparison_phase8.py` via MECHANISM_ORDER + PHASE8_DEFAULTS.update | ✅ Done |
| 2026-06-05 | Configure SECTORAL overrides for US, Singapore, Laissez_Faire | ✅ Done |
| 2026-06-05 | 33/33 mechanism unit tests pass | ✅ Done |
| 2026-06-05 | 16/16 inequality mechanism unit tests pass | ✅ Done |
| 2026-06-05 | 9/9 country backtests pass | ✅ Done |
| 2026-06-05 | Full 11-system × 2-seed comparison runs clean | ✅ Done |

## Current State After Completion
| Metric | Value |
|--------|-------|
| Total mechanisms | 20+ missing mechs + core mechanisms |
| Unit tests | 33/33 pass, 16/16 pass |
| Backtests | 9/9 pass |
| System models | 11 (LS_Full, Dual_Compact_LS, Mutualist_LS, Pure_Georgist, Harberger_Georgist, US_Style, Nordic, Worker_Coop, UBI_VAT, Laissez_Faire, Singapore) |
| US Gini (2-seed) | 0.70 (real ~0.49) ← overshoot |
| Singapore Gini (2-seed) | 0.61 (real ~0.46) ← overshoot |

## Next Steps (pending debate)
1. ~~Calibrate mechanism parameters — US and Singapore Gini overshoot real values.~~ ✅ Done
2. ~~Full multi-seed comparison — Run 5+ seeds × 11 systems for statistical validity~~ ✅ Done
3. ~~Pareto frontier analysis — Run run_pareto.py with new data to find frontier~~ ✅ Done
4. **Cross-session champion persistence** — Save best comparison results for reference
5. **Analysis report** — Generate summary tables and visualizations

## Key Results After Calibration

### 13-System Pareto Frontier (China + India added)
| Rank | System | $Mean | Gini | Frontier | Composite |
|------|--------|------|------|----------|-----------|
| 1 | Laissez_Faire | $5,723K | 0.867 | ✅ | 1.29 |
| 2 | Singapore | $3,647K | 0.458 | ✅ | 1.15 |
| 3 | **Worker_Coop** | $1,963K | 0.223 | ✅ | **1.12** |
| 4 | **Pure_Georgist** | $1,970K | 0.252 | ✅ | **1.09** |
| 5 | **Mutualist_LS** | $2,000K | 0.275 | ✅ | **1.06** |
| 6 | **LS_Full** | $2,028K | 0.304 | ✅ | **1.03** |
| 7 | Dual_Compact_LS | $1,812K | 0.187 | ✅ | 1.00 |
| 8 | Harberger_Georgist | $2,099K | 0.392 | ✅ | 0.98 |
| 13 | **India** | $1,256K | 0.484 | ❌ | **-0.30** |

**New findings:** China (Gini 0.462, $1.58M) and India (Gini 0.484, $1.26M) are both Pareto-dominated. The LS cluster holds its frontier position against fundamentally different economic architectures (state capitalism, informal dominance). India scores worst on composite measure due to low CRRA welfare.

## Deviation Log
| 2026-06-04 | SECTORAL overrides missing education_variance for all systems | Forgot to include critical wage dispersion parameter | Added education_variance and wage_dispersion_mult to every system in SECTORAL |
| 2026-06-04 | Singapore CPF externalities weren't firing in full comparison | CPF mechanisms not in SECTORAL (only in test SYS dict) | Added cpf_liquidity_trap, cpf_demand_suppression, cpf_housing_feedback, cpf_opportunity_cost to Singapore SECTORAL override |
| 2026-06-04 | Laissez-Faire Gini was 0.10 (target 0.50) | Missing education_variance and wage_dispersion_mult for Laissez_Faire | Added education_variance=0.8, wage_dispersion_mult=3.0 to Laissez_Faire SECTORAL |
