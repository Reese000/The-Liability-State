# Parameter Audit: Empirically Grounded vs Vibes-Based

**Date:** 2026-06-04  
**Purpose:** Identify every parameter value in the simulation that was chosen for flavor ("vibes") rather than from empirical data, and document which ones materially affect results.

---

## Layer 1: Global Constants (comparison_phase4.py)

| Constant | Value | Source | Classification |
|----------|-------|--------|---------------|
| `STEPS` | 480 | Chosen for 40-year sim at 12 steps/year | **STRUCTURAL** — arbitrary but consistent |
| `SEEDS` | 1-5 | Chosen for statistical stability | **STRUCTURAL** |
| `HOURS_PER_STEP` | 160 | Standard 40h/wk × 4 weeks | **EMPIRICAL** |
| `LVT_ANNUAL_RATE` | 3% | Common Georgist proposal range | **STRUCTURAL** — standard LVT rate |
| `INVESTMENT_RATE` | 0.3 | Rough estimate of retained earnings → investment | ⚠️ **VIBES** |
| `BUSINESS_WAGE_BILL` | $5,000/mo | Rough average per business | ⚠️ **VIBES** |
| `WAGE_VARIABILITY` | (0.92, 1.0) | Narrow range to prevent wage explosion | ⚠️ **VIBES** |
| `ACCIDENT_PROBABILITY` | 0.02 | 2% monthly accident rate | ⚠️ **VIBES** — no citation |
| `TFP_TAX_ELASTICITY` | -0.15 | Rough inverse of tax rate effect on TFP | ⚠️ **VIBES** — replaced by `tax_efficiency_loss` |
| `LABOR_SUPPLY_ELASTICITY` | 0.2 | Lower end of empirical range (Chetty 2012: 0.2-0.5) | **EMPIRICAL** |
| `ADMIN_OVERHEAD_BY_TAX` | LVT=1%, income=8%, VAT=5%, corp=6%, none=0% | LVT is lowest (efficient), income tax high (IRS overhead + compliance) | **PARTIALLY EMPIRICAL** — direction correct, exact values guessed |

---

## Layer 2: Phase 4 System Configs (comparison_phase4.py `_mk()`)

These are the **most dangerous** vibes-based parameters — they're embedded in every system's base config and differ wildly between systems.

### Parameter: `economies_of_scale` (0 to 0.15)

**What it does:** Scales business TFP with log(capital/50000). At 0.15 with $500K capital, gives +34.5% TFP boost.

| System | Value | Classification | Justification |
|--------|:-----:|:-------------:|---------------|
| Laissez_Faire | **0.15** | ❌ **VIBES** | "LF should have high scale efficiency" |
| US_Style | 0.08 | ❌ **VIBES** | "US should have moderate scale" |
| Nordic | 0.06 | ❌ **VIBES** | "Nordic small biz emphasis" |
| Singapore | 0.07 | ❌ **VIBES** | "Singapore efficient" |
| LS_Full | 0.05 | ❌ **VIBES** | "LS should have moderate scale" |
| Pure_Georgist | 0.0 | ❌ **VIBES** | "Pure georgist = small scale" |

**Impact on $6M vs $2M gap: HIGH.** LF's 3x higher economies_of_scale than LS_Full compounds every step, giving LF businesses a massive TFP advantage that has nothing to do with the tax system.

### Parameter: `monopoly_markup_max` (1.0 to 1.6)

**What it does:** Maximum markup multiplier on business revenue, scaled by market share.

| System | Value | Classification |
|--------|:-----:|:-------------:|
| Laissez_Faire | **1.6** | ❌ **VIBES** — "LF should have high monopoly power" |
| US_Style | 1.4 | ❌ **VIBES** |
| Singapore | 1.35 | ❌ **VIBES** |
| Nordic | 1.3 | ❌ **VIBES** |
| LS_Full | 1.2 | ❌ **VIBES** |
| Pure_Georgist | 1.1 | ❌ **VIBES** |
| Worker_Coop | 1.1 | ❌ **VIBES** |

**Impact on $6M vs $2M gap: HIGH.** LF's 33% higher markup cap than LS compounds into higher retained profits.

### Parameter: `inheritance_rate` (0 to 0.5)

**What it does:** Fraction of wealth redistributed as inheritance (post-simulation, flat equal redistribution in Phase 4).

| System | Value | Classification |
|--------|:-----:|:-------------:|
| Laissez_Faire | **0.5** | ❌ **VIBES** — "LF should have strong inheritance" |
| US_Style | 0.25 | ❌ **VIBES** |
| Nordic | 0.20 | ❌ **VIBES** |
| Singapore | 0.30 | ❌ **VIBES** |
| LS_Full | 0.10 | ❌ **VIBES** |
| Pure_Georgist | 0.0 | ❌ **VIBES** |

**Impact on $6M vs $2M gap: MEDIUM-HIGH.** 5x higher inheritance rate means more dynastic wealth accumulation.

### Parameter: `information_asymmetry` (0 to 0.5)

**What it does:** Modifies insurance premiums, detection probability, and market efficiency.

| System | Value | Classification |
|--------|:-----:|:-------------:|
| Laissez_Faire | **0.5** | ❌ **VIBES** — "LF should have asymmetric info" |
| US_Style | 0.35 | ❌ **VIBES** |
| Nordic | 0.20 | ❌ **VIBES** |
| Singapore | 0.15 | ❌ **VIBES** |
| LS_Full | 0.10 | ❌ **VIBES** |
| Pure_Georgist | 0.0 | ❌ **VIBES** |

**Impact: LOW-MEDIUM.** Affects insurance market efficiency but not a primary wealth driver.

### Parameter: `corruption_level` (0 to 0.15)

| System | Value | Classification |
|--------|:-----:|:-------------:|
| Laissez_Faire | **0.0** | ❌ **VIBES** — contradicts low enforcement |
| US_Style | 0.15 | ❌ **VIBES** |
| Nordic | 0.05 | ❌ **VIBES** |
| Singapore | 0.01 | ❌ **VIBES** |
| LS_Full | 0.02 | ❌ **VIBES** |

**Impact: LOW.** Corruption causes small penalty taxes.

### Parameter: `enforcement_quality` (0.2 to 0.95)

| System | Value | Classification |
|--------|:-----:|:-------------:|
| Laissez_Faire | **0.2** | ❌ **VIBES** — "LF should have weak courts" |
| LS_Full | **0.95** | ❌ **VIBES** — "LS should have strong courts" |
| Pure_Georgist | 0.5 | ❌ **VIBES** |
| US_Style | 0.7 | ❌ **VIBES** |
| Nordic | 0.85 | ❌ **VIBES** |
| Singapore | 0.9 | ❌ **VIBES** |

**Impact on $6M vs $2M gap: MEDIUM.** Higher enforcement means more court case victories and less evasion. But LF gets free courts despite 0.2 enforcement — the model doesn't penalize low enforcement enough.

### Parameter: `detection_probability_base` (0.1 to 0.8)

| System | Value | Classification |
|--------|:-----:|:-------------:|
| Laissez_Faire | **0.1** | ❌ **VIBES** |
| LS_Full | 0.7 | ❌ **VIBES** |

**Impact: LOW.**

### Parameter: `corp_tax_rate` (0 to 0.21)

| System | Value | Classification |
|--------|:-----:|:-------------:|
| US_Style | 0.21 | **EMPIRICAL** — matches US corporate rate |
| Nordic | 0.21 | **EMPIRICAL** — matches Nordic rate |
| Singapore | 0.17 | **EMPIRICAL** — matches Singapore rate |
| All others | 0 | **STRUCTURAL** |

### Parameter: `income_effect_labor` (0 to 0.12)

**What it does:** Modifies labor supply response based on cumulative transfers received.

| System | Value | Classification |
|--------|:-----:|:-------------:|
| US_Style | 0.08 | ❌ **VIBES** |
| Nordic | 0.10 | ❌ **VIBES** |
| Singapore | 0.03 | ❌ **VIBES** |

**Impact: LOW.** Minor labor supply distortion.

### Parameter: `admin_overhead` (0.01 to 0.08)

| System | Value | Classification |
|--------|:-----:|:-------------:|
| Laissez_Faire | 0.0 | **STRUCTURAL** — no tax = no overhead |
| LS_Full | 0.01 | **EMPIRICAL DIRECTION** — LVT has lowest admin cost |
| US_Style | 0.08 | ⚠️ **VIBES** — no citation for exact 8% |
| Nordic | 0.06 | ⚠️ **VIBES** |

### Parameter: `banking_multiplier` (0 to 5)

**What it does:** Legacy — how much banks can multiply deposits into loans.

| System | Value | Classification |
|--------|:-----:|:-------------:|
| Laissez_Faire | **5** | ❌ **VIBES** — replaced by reserve_requirement |
| US_Style | 3 | ❌ **VIBES** |
| Nordic | 2.5 | ❌ **VIBES** |
| LS_Full | 0 | ❌ **VIBES** |

**Impact: MEDIUM.** LF's 5x banking multiplier (vs LS 0) massively amplifies credit creation. This alone could explain a large chunk of the wealth gap. **Legacy parameter — replaced by reserve_requirement which is 0 for all systems.**

---

## Layer 3: Phase 5 Overrides (comparison_phase5.py)

| Parameter | Classification | Notes |
|-----------|:-------------:|-------|
| `use_harberger` | **STRUCTURAL** — system design choice | LS systems get Harberger self-assessment |
| `minimum_wage` | **EMPIRICAL** for US ($7.25/hr) | Other systems = 0 (no min wage) |
| `foreign_ownership_allowed` | **STRUCTURAL** | LS systems restrict foreign ownership |
| `migration_enabled` | **STRUCTURAL** | Dual_Compact only |

---

## Layer 4: Phase 8 Defaults (comparison_phase8.py)

| Parameter | Default | Classification |
|-----------|:-------:|:-------------:|
| `labor_supply_elasticity` | 0.2 | **EMPIRICAL** (Chetty 2012 range) |
| `money_creation_rate` | 0.0 | **DEFAULT OFF** |
| `tax_efficiency_loss` | 0.0 | **DEFAULT OFF** (Chetty-based when on) |
| `healthcare_gdp_share` | 0.0 | **STRUCTURAL** — system-specific |
| `education_gdp_share` | 0.0 | **STRUCTURAL** — system-specific |
| `carbon_tax_rate` | 0.0 | **STRUCTURAL** — system-specific |
| `elite_capture_intensity` | 0.0 | **DEFAULT OFF** |
| `education_variance` | 0.0 | **DEFAULT OFF** — primary Gini driver when on |
| `wage_dispersion_mult` | 1.0 | **DEFAULT OFF** |
| All inequality params | 0.0/False | **DEFAULT OFF** — all vibes-based when active |

---

## Layer 5: SECTORAL Overrides (comparison_phase8.py)

These are the parameters we just tuned. Assessed individually:

| Parameter | Empirically Grounded? | Notes |
|-----------|:---------------------:|-------|
| `education_variance` US=0.7 | **PARTIAL** — Direction correct (US has high edu inequality), exact value is vibes | Matches real wage dispersion if combined with wage_dispersion_mult |
| `education_variance` SG=0.7 | **PARTIAL** — Singapore has high education streaming | Could be 0.5-0.7 range |
| `education_variance` Nord=0.4 | **PARTIAL** — Nordic has compressed education system | Reasonable range |
| `immigrant_share` SG=0.42 | **EMPIRICAL** — matches 42% foreign workforce | ✓ |
| `immigrant_share` US=0.15 | **EMPIRICAL** — matches ~15% foreign-born | ✓ |
| `immigrant_wage_penalty` SG=0.70 | **PARTIAL** — guest workers earn 50-70% less | Reasonable upper bound |
| `structural_gap_groups` US=[0.87,0.13] | **EMPIRICAL** — 13% Black population | ✓ |
| `structural_gap_multipliers` US=[1.0,0.15] | **EMPIRICAL** — Black/white wealth ratio ~15% | ✓ |
| `power_law_exponent` US=0.28 | **PARTIAL** — Fagereng et al. find ~0.3-0.5 return premium scaling | Reasonable |
| `cpf_liquidity_trap` | **PARTIAL** — direction correct, magnitude estimated | |
| All inheritance values | **PARTIAL** — direction correct (conc should be high), exact values vibes | |
| `forced_reinvestment` | **STRUCTURAL** — design choice to close hoarding loophole | |

---

## Summary: What's Actually Vibes-Based and Matters

### High Impact (explains most of $6M vs $2M gap)

| Parameter | LF Value | LS Value | Ratio | Why It's Vibes |
|-----------|:--------:|:--------:|:-----:|:---------------|
| **`economies_of_scale`** | 0.15 | 0.05 | 3x | No citation — picked to "feel right" |
| **`monopoly_markup_max`** | 1.6 | 1.2 | 1.33x | No citation — picked to "feel right" |
| **`banking_multiplier`** | 5 | 0 | ∞ | Legacy — replaced by reserve_requirement=0 for all |
| **`inheritance_rate`** | 0.5 | 0.1 | 5x | Old flat mechanism — now replaced by inheritance_conc |

### Medium Impact

| Parameter | LF Value | LS Value | Notes |
|-----------|:--------:|:--------:|:------|
| `enforcement_quality` | 0.2 | 0.95 | Model doesn't penalize low enforcement enough to matter |
| `information_asymmetry` | 0.5 | 0.1 | Small effect on insurance |
| `admin_overhead` | 0.0 (none) | 0.01 (lvt) | Small — 1% leakage doesn't explain gap |

### Low Impact

| Parameter | Notes |
|-----------|-------|
| `corruption_level` | Small tax penalty |
| `income_effect_labor` | Minor labor supply effect |
| `detection_probability_base` | Affects evasion, small effect |
| `wage_ratio_cap` | Only matters for worker coop |

### The Core Finding

**The $6M vs $2M gap between Laissez-Faire and LS_Full is NOT primarily about the 0.3% Alliance skim.** It's driven by:

1. **economies_of_scale (3x advantage for LF)** — biggest single driver
2. **banking_multiplier (5 vs 0)** — massive credit creation
3. **monopoly_markup_max (33% higher for LF)** — more retained profits
4. **inheritance_rate (5x higher for LF)** — dynastic wealth accumulation

These were all chosen as "vibes" in Phase 4 — they reflect the designer's intuition about what each system "should look like" rather than empirical data. An unbiased comparison would equalize these across systems.

### What We Fixed vs What Remains

**Fixed in this iteration:**
- Removed `gov_service_productivity` (was +11% wealth bonus for income-tax systems)
- Added `forced_reinvestment` (closes LF cash-hoarding loophole)
- All inequality mechanisms are default OFF, empirically grounded when on

**Still broken (vibes-based in Phase 4):**
- `economies_of_scale` — needs equalizing or removing
- `monopoly_markup_max` — needs equalizing
- `banking_multiplier` — already 0 for all via reserve_requirement, but Phase 4 legacy still has non-zero values
- `inheritance_rate` — replaced by `inheritance_flow_fraction` in current runs, but Phase 4 legacy still fires

**Recommendation:** Equalize economies_of_scale and monopoly_markup_max across all systems, or move them to config-driven SECTORAL parameters with explicit justification when they differ.
