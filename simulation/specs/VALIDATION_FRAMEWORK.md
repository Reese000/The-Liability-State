# Validation Framework — The Liability State

> **Version:** 1.0  
> **Scope:** Defines how each LS mechanic is validated against real-world economic phenomena before full integration. Specifies test scenarios, expected behaviors, acceptance criteria (quantitative thresholds), baseline real-world phenomena, and execution procedures for stages V1–V4 plus additional stages and full system integration.  
> **Philosophy:** Tiered, mixed-methods validation combining qualitative pattern matching (generous tolerance bands for partial-equilibrium emergence) with quantitative statistical thresholds (tight gates on robust moments at system level). Adapted from the Agent-Critic debate: rigor without overconstraining minimal generative models.

---

## Table of Contents

1. [Validation Philosophy & Tiered Architecture](#1-validation-philosophy--tiered-architecture)
2. [Stage V1 — Insurance Adverse Selection (Akerlof's Lemons)](#2-stage-v1--insurance-adverse-selection-akerlofs-lemons)
3. [Stage V2 — LVT vs Income Tax Efficiency (Georgist)](#3-stage-v2--lvt-vs-income-tax-efficiency-georgist)
4. [Stage V3 — Tort Liability Deterrence (Law & Economics)](#4-stage-v3--tort-liability-deterrence-law--economics)
5. [Stage V4 — Harberger Convergence](#5-stage-v4--harberger-convergence)
6. [Additional Stages](#6-additional-stages)
   - [V5 — Citizen's Dividend & Wealth Redistribution](#61-v5--citizens-dividend--wealth-redistribution)
   - [V6 — Insurance Market Solvency & Catastrophic Risk](#62-v6--insurance-market-solvency--catastrophic-risk)
   - [V7 — Fraud Prevention Stack (Game-Theoretic Deterrence)](#63-v7--fraud-prevention-stack-game-theoretic-deterrence)
   - [V8 — Court System Throughput & Docket Dynamics](#64-v8--court-system-throughput--docket-dynamics)
   - [V9 — Opt-In Guild Market Power & Rent-Seeking](#65-v9--opt-in-guild-market-power--rent-seeking)
7. [Full Integrated System Validation](#7-full-integrated-system-validation)
8. [Validation Execution Protocol](#8-validation-execution-protocol)
9. [Regression Testing & CI Integration](#9-regression-testing--ci-integration)
10. [Appendix: Common Parameter Templates](#10-appendix-common-parameter-templates)

---

## 1. Validation Philosophy & Tiered Architecture

### 1.1 Design Principles

The Liability State is a **minimalist generative model** — agents are boundedly rational utility-maximizers operating under incomplete information. It is not an econometric forecasting tool. Validation must therefore:

1. **Accept sign consistency and order-of-magnitude plausibility** for partial-equilibrium effects (V1–V2 level).
2. **Require simultaneous quantitative matching of multiple robust moments** at system level (V3–V4 and integrated), with empirical uncertainty built into tolerance thresholds.
3. **Use cross-country / cross-period pattern validation** to prevent overfitting to any single historical episode.
4. **Report predictive distributions** that incorporate both parameter and structural uncertainty.

### 1.2 Tiered Decision Gates

| Tier | Scope | Tolerance | Method | Falsification Rule |
|------|-------|-----------|--------|--------------------|
| **T1: Directional** | V1–V2 isolated tests | Sign + order-of-magnitude (2× of plausible range) | N deterministic runs; check sign & plausible magnitude | Fails if sign is wrong or magnitude is >2× known range |
| **T2: Statistical** | V3–V4 isolated tests | 95% CI of empirical meta-distribution | N=100 Monte Carlo runs; bootstrap CI vs empirical moments | Fails if model mean falls outside bootstrapped 95% CI |
| **T3: Systemic** | Full integration | Qualitative pattern + multiple simultaneous moment bounds | N=500 runs across parameter sweep; cross-country/period validation | Fails if any of 5+ key system patterns are absent or outside generous bounds |

### 1.3 Pre-Registration Requirement

Before any validation run, the specific test parameters (N runs, tolerance thresholds, random seeds, parameter values) MUST be recorded in a validation plan. Changes to the plan mid-run constitute a **Decision Gate** event and must be logged in the Risk Register (see `tasks.md`).

---

## 2. Stage V1 — Insurance Adverse Selection (Akerlof's Lemons)

### 2.1 Baseline Real-World Phenomenon

Akerlof (1970) ["The Market for 'Lemons'"] demonstrates that asymmetric information between buyers and sellers can drive high-quality goods out of a market. In insurance: when buyers know their risk level better than insurers, low-risk individuals are overcharged relative to their true risk, causing them to drop out. The pool becomes riskier, premiums rise further, and the market may collapse entirely (death spiral).

**Key empirical signatures:**
- Negative correlation between pooled risk level and market participation
- Above some adverse selection threshold, market participation drops discontinuously
- High-risk agents constitute a growing fraction of the insured pool over time
- Premiums rise monotonically as low-risk agents exit

### 2.2 Test Scenario

```
Environment: Single-compact insurance market with N=1000 agents
- Agents have heterogeneous risk types: low (p_loss=0.02), medium (p_loss=0.05), high (p_loss=0.15)
- Fraction of high-risk agents: configurable parameter f_high ∈ [0.05, 0.40]
- Insurer offers a single pooled premium (cannot discriminate by risk type)
- Agents choose to buy insurance if EU(insured) > EU(uninsured)
- No mandatory purchase requirement (opt-in insurance)
Duration: T=200 ticks (steady-state equilibrium)
```

**Variations:**
- **V1a — Baseline:** f_high = 0.10 (low adverse selection pressure)
- **V1b — Death Spiral:** f_high = 0.25 (high adverse selection pressure)
- **V1c — Mandatory Pooling:** same as V1a but with mandatory purchase (control)

### 2.3 Expected Behavior

1. In V1a (low f_high): partial adverse selection — low-risk agents drop out, medium-risk partially participate, high-risk fully insured. Market functions but with elevated premiums.
2. In V1b (high f_high): full death spiral — no equilibrium with positive participation at any premium. Market collapses.
3. Risk composition of insured pool shifts monotonically toward high-risk.
4. Premiums exceed actuarially fair level for the average risk.

### 2.4 Acceptance Criteria (Quantitative Thresholds)

| Criterion | Metric | Threshold | Tier |
|-----------|--------|-----------|------|
| Adverse selection direction | Correlation(risk_level, insured_flag) | Must be POSITIVE (higher risk → more likely insured) | T1 |
| Pool composition shift | Δ(% high-risk in pool) from t=0 to t=200 | ≥ +10 percentage points (for f_high≥0.15) | T1 |
| Premium wedge | (Actual premium) / (Actuarially fair premium for pool avg) | > 1.0 (must exceed fair premium) | T1 |
| Market collapse threshold | f_high at which market participation drops to <5% | Must exist within f_high ∈ [0.15, 0.35] | T2 |
| Death spiral discontinuity | Participation(f_high) curve | Must show a sharp drop (>50% participation loss over ≤0.05 change in f_high) | T2 |
| No adverse selection in mandatory | V1c: Low-risk participation | Must be >90% (control: mandatory eliminates selection) | T1 |

### 2.5 How to Run the Test

```python
# Pseudocode execution plan
def run_v1():
    for f_high in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]:
        for seed in range(50):  # Monte Carlo
            sim = Simulation(config=Config(
                n_agents=1000,
                risk_distribution={
                    'low': {'p_loss': 0.02, 'fraction': 1 - f_high - 0.2},
                    'medium': {'p_loss': 0.05, 'fraction': 0.2},
                    'high': {'p_loss': 0.15, 'fraction': f_high}
                },
                pooled_premium_only=True,
                mandatory_insurance=False,
                n_ticks=200
            ))
            sim.run()
            results[f_high][seed] = {
                'participation_rate': sim.market.insured_count / 1000,
                'pool_avg_risk': sim.market.insured_pool_avg_p_loss,
                'premium': sim.market.premium,
                'fair_premium': sim.market.actuarially_fair_premium()
            }
    # Check: participation discontinuity, premium wedge, pool shift
    validate_t1(results)
    validate_t2(results)  # bootstrap CI for collapse threshold
```

### 2.6 Failure Interpretation

| Failure Mode | Likely Cause | Remediation |
|-------------|--------------|-------------|
| No adverse selection at any f_high | Agent utility function doesn't penalize overpriced insurance enough | Adjust risk aversion parameter γ or add reference-dependent utility |
| Death spiral too early (f_high < 0.10) | Low-risk agents too sensitive to premium; check risk aversion | Calibrate risk aversion from empirical insurance demand elasticities |
| Premium wedge < 1.0 | Insurer pricing rule not covering pool risk; check premium formula | Fix premium = (expected_loss + loading) / (1 - default_probability) |
| No discontinuity (smooth decline) | Pooled pricing with continuous exit; check if market microstructure creates feedback loop | Add fixed transaction cost or search friction |

---

## 3. Stage V2 — LVT vs Income Tax Efficiency (Georgist)

### 3.1 Baseline Real-World Phenomenon

Georgist economic theory (Henry George, 1879) posits that a tax on **land value** (LVT) is efficient because land supply is fixed — the tax cannot distort the supply of the taxed factor. By contrast, a tax on **labor income** creates a deadweight loss by reducing labor supply below the efficient level. The key empirical prediction: LVT has a smaller negative impact on GDP/output than an equivalent-yield income tax.

**Key empirical signatures:**
- Income tax reduces labor supply (hours worked, participation rate) with elasticity ~0.1–0.4
- LVT (on unimproved land value) shows no statistically significant labor supply effect
- Over generations, LVT jurisdictions show higher capital formation (since improvements are untaxed)
- Equivalent-yield LVT generates higher total output than income tax

### 3.2 Test Scenario

```
Environment: Two otherwise identical compacts running in parallel (or sequentially on same agent population)
- Compact A: LVT-only (tax on land value, rate = r_lvt)
- Compact B: Income-tax-only (tax on labor earnings, rate = r_inc)
- Revenue must be equalized: r_lvt * total_land_value = r_inc * total_labor_income
- Agents: N=500 workers, N=50 businesses (employers)
- Workers choose labor supply (hours worked) given after-tax wage
- Both compacts return tax revenue as lump-sum dividend (controlling for spending effect)
Duration: T=500 ticks (captures long-run equilibrium)
```

**Variations:**
- **V2a — Low Tax:** Revenue target = 5% of GDP
- **V2b — High Tax:** Revenue target = 20% of GDP
- **V2c — Land as Fixed Factor:** Both compacts start with identical land distribution

### 3.3 Expected Behavior

1. Compact B (income tax) shows lower total labor supply than Compact A (LVT) at equivalent revenue.
2. Compact A shows no change in labor supply relative to no-tax baseline.
3. The GDP gap between A and B grows with the tax rate (higher deadweight loss from income tax at higher rates).
4. Compact A shows higher investment in land improvements (capital formation).
5. Land prices adjust downward in Compact A, partially capitalizing the tax.

### 3.4 Acceptance Criteria (Quantitative Thresholds)

| Criterion | Metric | Threshold | Tier |
|-----------|--------|-----------|------|
| Labor supply distortion | Δ(hours_worked) from no-tax baseline: LVT vs income tax | LVT: |Δ| ≤ 2%; Income tax: |Δ| ≥ 3% | T1 |
| GDP differential | GDP_A / GDP_B at equivalent revenue | Must be ≥ 1.02 (2% advantage for LVT) at high-tax (V2b) | T1 |
| Tax elasticity of labor | ε = %Δlabor / %Δtax_rate for income tax | Must be negative, magnitude ∈ [0.05, 0.5] | T2 |
| LVT distortion neutrality | ε_lvt (elasticity of labor wrt LVT rate) | 95% CI must include zero | T2 |
| Capital formation | Investment in improvements per agent, A vs B at t=500 | A ≥ B (with p < 0.05) | T2 |
| Revenue equivalence | |Total_Revenue_A - Total_Revenue_B| / Total_Revenue | ≤ 5% (controlling for GDP differences) | T1 |
| Labor participation gap | (Participation rate_A - Participation rate_B) at high tax | ≥ 3 percentage points | T1 |

### 3.5 How to Run the Test

```python
def run_v2():
    for tax_level in ['low', 'high']:
        revenue_target = 0.05 * baseline_gdp if tax_level == 'low' else 0.20 * baseline_gdp
        for seed in range(100):
            # Generate baseline (no tax)
            base = Simulation(config=Config(n_agents=500, n_businesses=50, lvt_rate=0, income_tax_rate=0, n_ticks=500))
            base.run()
            baseline_gdp = base.gdp_history[-100:].mean()
            
            # Compact A: LVT
            r_lvt = calibrate_lvt_rate(revenue_target, base.land_values)
            sim_a = Simulation(config=Config(n_agents=500, n_businesses=50, lvt_rate=r_lvt, income_tax_rate=0, n_ticks=500))
            sim_a.run()
            
            # Compact B: Income tax
            r_inc = calibrate_income_tax_rate(revenue_target, base.labor_income)
            sim_b = Simulation(config=Config(n_agents=500, n_businesses=50, lvt_rate=0, income_tax_rate=r_inc, n_ticks=500))
            sim_b.run()
            
            results[tax_level][seed] = {
                'gdp_a': sim_a.gdp, 'gdp_b': sim_b.gdp,
                'labor_a': sim_a.total_hours, 'labor_b': sim_b.total_hours,
                'revenue_a': sim_a.total_lvt, 'revenue_b': sim_b.total_income_tax,
                'capital_a': sim_a.capital_investment, 'capital_b': sim_b.capital_investment
            }
    validate_tier1(results)
    validate_tier2(results)  # bootstrap CI for elasticities
```

### 3.6 Failure Interpretation

| Failure Mode | Likely Cause | Remediation |
|-------------|--------------|-------------|
| LVT shows positive labor distortion | Agent utility function treats land wealth as fungible with labor income; agents reduce labor to stay below LVT threshold | Ensure LVT is on **unimproved** land value only; separate agent's labor decision from land holding |
| Income tax shows no labor effect | Labor supply elasticity too low; check leisure preference in utility | Calibrate Frisch elasticity from macro literature (target: 0.2–0.5) |
| Revenue equivalence fails | Tax base erosion different between systems | Check that LVT base (land value) doesn't collapse; income tax base may shrink endogenously |
| GDP gap doesn't widen with tax rate | Both taxes affect same channel (e.g., both reduce investment) | Check that improvements are truly exempt under LVT; consider separable capital/land production function |

---

## 4. Stage V3 — Tort Liability Deterrence (Law & Economics)

### 4.1 Baseline Real-World Phenomenon

Law-and-economics theory (Becker, 1968; Shavell, 1987) predicts that **tort liability** (the threat of being sued for damages) deters harmful behavior when the expected cost of liability exceeds the benefit of the harmful activity. Key predictions:
- Higher liability exposure → lower accident/incident rates (deterrence effect)
- The deterrent effect diminishes at high liability levels (satiation — fully careful already)
- Strict liability and negligence standards produce different deterrence profiles
- Liability insurance partially dilutes deterrence (moral hazard channel)

**Key empirical signatures:**
- Negative elasticity of accident rate with respect to expected liability cost
- Industry/product recalls decrease when liability standards tighten
- Physicians in high-liability specialties (e.g., neurosurgery) practice more defensive medicine
- No significant additional deterrence beyond some liability threshold (plateau)

### 4.2 Test Scenario

```
Environment: Single compact with N=200 businesses producing a good with a probabilistic side-effect (accidents)
- Each business chooses a safety level s ∈ [0, 1] at cost C(s) (increasing convex)
- Accidents occur with probability p(s) = p_min + (1 - p_min) * (1 - s)²
- When an accident occurs, a victim (random worker/citizen) suffers loss L
- Victim can file a tort claim in court; court awards damages D (configurable fraction of loss)
- Businesses can purchase liability insurance (optional)
Duration: T=500 ticks
```

**Variations:**
- **V3a — No Liability:** D = 0 (control: no deterrence)
- **V3b — Strict Liability:** D = L (full damages, no negligence defense)
- **V3c — Partial Liability:** D = 0.5 * L
- **V3d — Negligence Standard:** D = L only if s < s_standard (due-care standard)
- **V3e — Liability + Insurance:** Same as V3b but businesses can buy insurance

### 3 Key Empirical Signatures (V3a–V3e must collectively reproduce)

### 4.3 Expected Behavior

1. Average safety level s increases from V3a (zero) → V3b (strict liability) → V3c (partial) monotonically.
2. Accident rate p(s) decreases correspondingly.
3. Deterrence plateaus: increasing damages beyond ~L (full compensation) does not further reduce accidents.
4. Negligence standard (V3d) produces safety levels near the due-care standard s_standard.
5. Insurance (V3e) partially reduces deterrence (moral hazard: insured businesses choose lower safety).
6. Court caseload rises with liability exposure (more claims filed).

### 4.4 Acceptance Criteria (Quantitative Thresholds)

| Criterion | Metric | Threshold | Tier |
|-----------|--------|-----------|------|
| Deterrence direction | Safety level s in V3a vs V3b | s_V3b > s_V3a (p < 0.01) | T1 |
| Deterrence elasticity | ε = %Δaccident_rate / %Δexpected_liability | Negative, ∈ [-0.8, -0.05] | T2 |
| Deterrence plateau | Δs between V3b (D=L) and V3b' (D=2L) | ≤ 0.05 (diminishing returns) | T1 |
| Negligence targeting | |s_V3d - s_standard| / s_standard | ≤ 15% | T2 |
| Moral hazard effect | s_V3e (with insurance) vs s_V3b (without) | s_V3e ≤ s_V3b (p < 0.05) | T1 |
| Insurance pooling | Insurance uptake across risk levels | Higher-risk businesses more likely to insure | T1 |
| Court utilization | Cases_filed_V3b / Cases_filed_V3a | ≥ 5× (liability increases litigation) | T1 |
| Accident rate baseline | p(s) in V3a (no liability) | Must be close to p_min + (1-p_min) * 1.0 = ~1.0 | T1 |

### 4.5 How to Run the Test

```python
def run_v3():
    configs = {
        'no_liability': {'damage_multiplier': 0.0, 'negligence_standard': None, 'insurance_available': False},
        'strict_full':   {'damage_multiplier': 1.0, 'negligence_standard': None, 'insurance_available': False},
        'strict_double': {'damage_multiplier': 2.0, 'negligence_standard': None, 'insurance_available': False},
        'partial':       {'damage_multiplier': 0.5, 'negligence_standard': None, 'insurance_available': False},
        'negligence':    {'damage_multiplier': 1.0, 'negligence_standard': 0.6, 'insurance_available': False},
        'with_insurance':{'damage_multiplier': 1.0, 'negligence_standard': None, 'insurance_available': True},
    }
    for label, cfg in configs.items():
        for seed in range(100):
            sim = Simulation(config=Config(
                n_businesses=200, n_workers=500,
                accident_p_min=0.01, accident_loss=100.0,
                **cfg, n_ticks=500
            ))
            sim.run()
            results[label][seed] = {
                'avg_safety': sim.businesses.safety.mean(),
                'accident_rate': sim.records.accidents / sim.records.total_production,
                'cases_filed': sim.court.cases_filed,
                'insurance_uptake': sim.businesses.insured.mean() if cfg['insurance_available'] else 0.0
            }
    validate_all(results)
```

### 4.6 Failure Interpretation

| Failure Mode | Likely Cause | Remediation |
|-------------|--------------|-------------|
| No deterrence effect | Expected liability cost too low relative to safety investment cost; agents don't respond to legal threat | Increase damages or reduce cost of safety; check agent decision horizon (short-sighted agents ignore low-probability liability) |
| Deterrence doesn't plateau | No satisficing on safety; agents optimize continuously as damages increase | Add convex safety cost function that makes perfect safety prohibitively expensive |
| Moral hazard too strong / too weak | Insurance premium not reflecting risk; check premium = f(safety) | Ensure actuarial pricing — insurers must adjust premiums based on observed safety choices |
| Negligence standard fails to anchor safety | Agents don't know the standard or can't compute it | Add information channel: courts publish negligence standard; agents observe it |

---

## 5. Stage V4 — Harberger Convergence

### 5.1 Baseline Real-World Phenomenon

Harberger taxation (Arnold Harberger, 1965) combines a **self-assessed property tax** with a **forced-sale right**: owners declare a value for their asset, pay tax on that value, and anyone can buy the asset at the declared price. This creates a theoretically self-enforcing mechanism:
- If you declare too low → you save on taxes but risk forced sale below market value
- If you declare too high → you pay excessive taxes
- Nash equilibrium converges to: declared value ≈ true market value

**Key empirical signatures:**
- Variance of declared-value-to-true-value ratio decreases over time (convergence)
- Forced sales occur primarily when declared values are significantly below market
- Tax rate inversely correlates with declared value (higher tax → lower declarations)
- Market efficiency increases (bid-ask spread narrows) after Harberger adoption

### 5.2 Test Scenario

```
Environment: Single compact with N=500 land parcels, each owned by one agent
- Agents have heterogeneous true valuations V_true_i ~ Uniform[10, 100]
- Each agent declares V_declare_i for their parcel
- Tax rate r_lvt is fixed (configurable; default 5%)
- In each tick, a random buyer agent may appear with probability p_buyer
- Buyer can purchase any parcel at its declared price V_declare_i
- Sellers may adjust declarations each tick (costly adjustment with friction)
Duration: T=1000 ticks
```

**Variations:**
- **V4a — Baseline:** r_lvt = 5%, p_buyer = 0.05
- **V4b — Low Tax:** r_lvt = 1%, p_buyer = 0.05
- **V4c — High Tax:** r_lvt = 15%, p_buyer = 0.05
- **V4d — Thin Market:** r_lvt = 5%, p_buyer = 0.01
- **V4e — Thick Market:** r_lvt = 5%, p_buyer = 0.20

### 5.3 Expected Behavior

1. Over time, the ratio V_declare / V_true converges toward 1.0 across parcels.
2. Convergence speed increases with p_buyer (market thickness) and decreases with r_lvt (tax distortion).
3. Surviving parcels (not force-sold) show tighter valuation ratios.
4. At equilibrium, forced-sale probability is roughly equal to the opportunity cost of under-declaring.
5. High-tax environments (V4c) produce lower declared values relative to true values (downward bias).

### 5.4 Acceptance Criteria (Quantitative Thresholds)

| Criterion | Metric | Threshold | Tier |
|-----------|--------|-----------|------|
| Convergence (sign) | d/dt of mean absolute deviation MAD = |V_declare/V_true - 1| | Negative trend (p < 0.05): valuations converge | T1 |
| Convergence magnitude | MAD(t=1000) - MAD(t=0) | Δ ≤ -0.15 (or ≤ 0.25 × MAD_initial, whichever is larger) | T1 |
| Steady-state accuracy | Median(V_declare/V_true) at t=1000 (V4a) | ∈ [0.80, 1.20] | T2 |
| Forced-sale efficiency | Correlation(V_declare/V_true, forced_sale_flag) | Negative: parcels with lower ratios are more likely to be sold | T1 |
| Tax distortion | Bias = Median(V_declare/V_true) V4c vs V4a | V4c median < V4a median (downward bias under high tax) | T1 |
| Market thickness effect | MAD(t=1000) V4d (thin) vs V4e (thick) | MAD_thin > MAD_thick (p < 0.05) | T2 |
| No explosive cycles | V_declare_i(t) for each parcel | Variance must be bounded (no infinite oscillation) | T1 |
| LVT revenue stability | Coefficient of variation of total LVT revenue (last 200 ticks) | CV ≤ 0.10 | T2 |

### 5.5 How to Run the Test

```python
def run_v4():
    configs = {
        'baseline': {'lvt_rate': 0.05, 'p_buyer': 0.05},
        'low_tax':  {'lvt_rate': 0.01, 'p_buyer': 0.05},
        'high_tax': {'lvt_rate': 0.15, 'p_buyer': 0.05},
        'thin_mkt': {'lvt_rate': 0.05, 'p_buyer': 0.01},
        'thick_mkt':{'lvt_rate': 0.05, 'p_buyer': 0.20},
    }
    for label, cfg in configs.items():
        for seed in range(100):
            sim = Simulation(config=Config(
                n_parcels=500, n_agents=500,
                true_valuations='uniform(10,100)',
                **cfg, n_ticks=1000,
                declaration_adjustment_cost=0.02  # friction
            ))
            sim.run()
            # Compute metrics each tick or at checkpoints
            ratios = [p.declared_value / p.true_value for p in sim.parcels if p.true_value > 0]
            results[label][seed] = {
                'mad_initial': mean_abs_deviation(ratios[:50]),
                'mad_final': mean_abs_deviation(ratios[-200:]),
                'median_ratio_final': np.median(ratios[-200:]),
                'forced_sales': sim.harberger_register.forced_sales_count,
                'revenue_cv': coeff_of_variation(sim.lvt_revenue_history[-200:]),
                'surviving_parcels_mean_ratio': surviving_ratio
            }
    validate_all(results)
```

### 5.6 Failure Interpretation

| Failure Mode | Likely Cause | Remediation |
|-------------|--------------|-------------|
| No convergence | Declared values don't adjust; check adjustment cost | Reduce adjustment friction or add updating heuristic (e.g., proportional adjustment toward market signal) |
| Oscillations (values bounce) | No memory in adjustment; agents overreact to forced-sale signals | Add inertia term λ in adjustment function: V_new = λ*V_old + (1-λ)*V_target |
| Systematic under-declaration persists | Forced-sale probability too low relative to tax savings | Increase p_buyer or decrease adjustment cost; check buyer rationality |
| Systematic over-declaration persists | No forced-sale mechanism working; buyers not arbitraging | Check that buyer agents are profit-seeking and have capital to purchase |
| Tax rate effect too large/small | Elasticity of declared value with respect to tax rate outside [−0.5, 0] | Calibrate via empirical LGT (land value tax) literature |

---

## 6. Additional Stages

### 6.1 V5 — Citizen's Dividend & Wealth Redistribution

#### 6.1.1 Baseline Real-World Phenomenon

Georgist economics also predicts that the **Citizen's Dividend** (equal lump-sum transfer of LVT revenue to all citizens) functions as a wealth floor without the distortion of means-tested welfare. The Alaska Permanent Fund Dividend (APFD) provides a real-world analog: annual equal cash transfers from resource revenue, with demonstrated effects on poverty reduction, consumption smoothing, and modest labor supply effects (Jones & Marquis, 2022).

**Key empirical signatures:**
- Dividend reduces wealth inequality (Gini coefficient decline)
- No significant negative labor supply effect (unlike means-tested welfare)
- Consumption floor stabilizes aggregate demand during downturns (automatic stabilizer)
- Dividend creates positive willingness-to-pay for jurisdiction membership

#### 6.1.2 Test Scenario

```
Environment: Single compact with N=500 agents, heterogeneous skills, endogenous labor market
- LVT collected → dividend pool → equal per-capita transfer to all citizens
- Compare to: (a) no dividend, (b) means-tested welfare (transfer only to below-threshold)
- Control for total fiscal expenditure equality
Duration: T=500 ticks
```

#### 6.1.3 Acceptance Criteria

| Criterion | Metric | Threshold | Tier |
|-----------|--------|-----------|------|
| Inequality reduction | Gini(wealth) with dividend vs without | Gini_dividend < Gini_no_dividend (p<0.05) | T1 |
| Labor distortion relative to welfare | Δ(labor supply) dividend vs means-tested | Dividend: |Δ|≤2%; Means-tested: |Δ|≥5% | T1 |
| Consumption floor effect | Min(consumption) during recession simulation | Dividend case ≥ 1.5× no-dividend case | T1 |
| Dividend as automatic stabilizer | StdDev(GDP) with dividend vs without | Ratio ≤ 0.85 (dividend dampens volatility) | T2 |
| Membership valuation | Willingness to pay for compact membership | Positive across wealth distribution | T1 |

### 6.2 V6 — Insurance Market Solvency & Catastrophic Risk

#### 6.2.1 Baseline Real-World Phenomenon

Insurance markets face systemic risk from **catastrophic correlated events** (e.g., hurricanes, pandemics). Standard insurance theory (Cummins, 2006) predicts that:
- Pool diversification works for uncorrelated risks but fails for systemic shocks
- Reinsurance and catastrophe bonds can restore solvency
- Without risk transfer, a large correlated loss triggers insurer default and cascading failure
- Premiums spike after catastrophic events (availability cycle)

#### 6.2.2 Test Scenario

```
Environment: Single compact, N=500 agents, N=5 insurers
- Each agent has independent small risk (p_loss=0.01, loss=10) plus correlated catastrophic risk
- Catastrophic event: all agents simultaneously face loss L_cat with probability p_cat per tick
- Insurers hold reserves = premiums collected − claims paid
- Solvency threshold: reserves < 0 → insurer defaults
Duration: T=2000 ticks with 1–3 catastrophic events
```

#### 6.2.3 Acceptance Criteria

| Criterion | Metric | Threshold | Tier |
|-----------|--------|-----------|------|
| Solvency failure without reinsurance | Insurer default rate when p_cat > premium_loading | Must show defaults (systemic risk exists) | T1 |
| Pool diversification | StdDev(insurer_loss) / StdDev(agent_loss) | < 1 for independent risks only; ≈ 1 for correlated | T1 |
| Premium cyclicality | Premium(t) before and after catastrophic event | After-event premium ≥ 1.3× before-event premium (for 10 ticks) | T1 |
| Reinsurance effectiveness | Default rate with vs without reinsurance market | Reinsurance reduces default rate by ≥50% | T2 |
| Market concentration | Herfindahl index of insurance market | Index rises after catastrophic events (weaker insurers exit) | T1 |

### 6.3 V7 — Fraud Prevention Stack (Game-Theoretic Deterrence)

#### 6.3.1 Baseline Real-World Phenomenon

The LS architecture includes five fraud prevention mechanisms: statistical audit, whistleblower bounties, staking, forced-sale discipline (Harberger), and reputation scoring. The effective deterrent should follow Becker's (1968) rational crime model:
- Detection probability × penalty > benefit of fraud → deterrence
- Multiple detection channels create redundancy (no single point of failure)
- Whistleblower incentives create decentralized monitoring

#### 6.3.2 Test Scenario

```
Environment: Single compact, N=500 agents, each agent can commit fraud (type T)
- Fraud types: premium evasion, insurance fraud, Harberger under-declaration, contract breach
- Each fraud type has configurable detection probability P_det, penalty Pen, and benefit B
- Agents decide rationally to commit fraud if B > P_det × Pen (modulated by honesty parameter θ)
- Check each prevention mechanism individually and in combination
Duration: T=300 ticks
```

#### 6.3.3 Acceptance Criteria

| Criterion | Metric | Threshold | Tier |
|-----------|--------|-----------|------|
| Rational deterrence | Fraud rate vs B/(P_det × Pen) across fraud types | Monotonically increasing: higher B/Penalty → higher fraud | T1 |
| Deterrence threshold | B/(P_det × Pen) at which fraud rate >10% | Should be ≈ 1.0 (Becker prediction) | T2 |
| Whistleblower effectiveness | Fraud rate with vs without whistleblower mechanism | Without > With (p<0.05) | T1 |
| Redundancy | Fraud rate with k=1 mechanism vs k=3 mechanisms | k=3 rate < k=1 rate (p<0.05) | T1 |
| Honesty parameter effect | Fraud rate for low-θ vs high-θ agents | Low-θ > High-θ (p<0.01) | T1 |
| False positive rate | Innocent agents penalized / total penalties | ≤ 5% (fraud detection must not harass honest agents) | T2 |

### 6.4 V8 — Court System Throughput & Docket Dynamics

#### 6.4.1 Baseline Real-World Phenomenon

Court systems face congestion when case filings exceed judge capacity, leading to:
- Backlog growth (cases pending > cases resolved per period)
- Settlement rate increases as backlog grows (parties prefer settlement to delayed trial)
- Filing costs and wait times create a "tax" on litigation
- Litigation volume is elastic to filing fees and expected wait time

#### 6.4.2 Test Scenario

```
Environment: Single compact with N_courts variable, each with capacity K_cases_per_tick
- Agents file cases when harmed; filing cost = F + time_cost × expected_wait
- Cases can be settled out of court (fraction configurable)
- Courts process cases FIFO; backlog accumulates
Duration: T=500 ticks
```

#### 6.4.3 Acceptance Criteria

| Criterion | Metric | Threshold | Tier |
|-----------|--------|-----------|------|
| Backlog growth | d(backlog)/dt when filing_rate > capacity | Must be positive (queue builds) | T1 |
| Settlement elasticity | %Δsettlement_rate / %Δbacklog | Positive (more backlog → more settlement) | T1 |
| Filing fee elasticity | %Δfilings / %Δfiling_fee | Negative, ∈ [-0.5, -0.05] | T2 |
| Capacity scaling | Backlog(N_courts=5) vs Backlog(N_courts=10) | Backlog_5 > Backlog_10 (p<0.05) | T1 |
| Litigation equilibrium | Stable or oscillatory? | Must converge to steady state (no infinite backlog under fixed parameters) | T1 |
| Judgment quality | Fraction of appealed cases | ≤ 10% (no systematic error) | T2 |

### 6.5 V9 — Opt-In Guild Market Power & Rent-Seeking

#### 6.5.1 Baseline Real-World Phenomenon

Occupational licensing and guilds create market power by restricting supply of labor. Key empirical observations (Kleiner & Krueger, 2013):
- Guild/licensed occupations earn wage premiums of 10–18% over comparable unlicensed workers
- Guild membership reduces labor supply in the guild sector
- Consumers pay higher prices but may receive higher quality (disputed)
- Guilds with excessive market power attract regulatory scrutiny and reform

#### 6.5.2 Test Scenario

```
Environment: Two-sector labor market (guild sector + open sector)
- N=500 workers choose sector; guild sector requires membership (cost + exam)
- Guild sets membership standards (quality floor) and may limit membership (quota)
- Businesses hire from guild pool for guild-sector jobs
Duration: T=500 ticks
```

#### 6.5.3 Acceptance Criteria

| Criterion | Metric | Threshold | Tier |
|-----------|--------|-----------|------|
| Wage premium | Guild wage / Open sector wage | > 1.0 (p<0.05), should be in [1.05, 1.25] (empirical range) | T2 |
| Supply restriction | Guild sector employment with guild vs without | Guild reduces employment by ≥ 10% | T1 |
| Quality effect | Guild sector defect/accident rate vs open sector | Guild ≤ Open (guilds may improve quality) | T1 |
| Rent-seeking dissipation | Guild revenue vs cost of guild operation | If revenue >> cost, rent-seeking persists | T1 |
| Competition erosion | Consumer surplus with vs without guild | Guild reduces consumer surplus (p<0.05) | T1 |

---

## 7. Full Integrated System Validation

### 7.1 Rationale

Individual mechanic validation (V1–V9) ensures each component works correctly in isolation. The full integrated system test validates that these mechanics interact plausibly — producing emergent macro phenomena that match real-world economic patterns. This is the **T3 Systemic** validation gate.

### 7.2 Baseline Real-World Phenomena (Integrated)

**P1 — Business Cycle with Leverage.** The system should generate endogenous business cycles: periods of expansion (rising employment, investment, land values) followed by contractions (falling employment, defaults, land value decline). Leverage dynamics (debt-financed investment) should amplify the cycle.

**P2 — Inequality Dynamics.** The interaction of LVT, insurance, tort liability, and guilds should produce realistic wealth/income distributions: right-skewed with a Gini coefficient in the observed range (0.35–0.60 for market income, 0.30–0.45 for post-fiscal income).

**P3 — Tax-Transfer Incidence.** The combined LVT + Dividend system should produce progressive net fiscal incidence: bottom quintile receives net transfer, top quintile pays net tax. Compare to real-world tax-benefit microsimulation benchmarks.

**P4 — Insurance-Legal Feedback.** Higher liability exposure should increase insurance uptake, which increases court filings (subrogation), which increases premium costs, which feeds back into safety investment. This feedback loop should produce a stable equilibrium (not explosion or collapse).

**P5 — Harberger-LVT-Dividend Loop.** Land values → LVT revenue → Dividend → consumption → land demand → land values. This circular flow must be stable and self-consistent.

**P6 — Compact Competition (Tiebout Sorting).** Multiple compacts with different policy bundles (LVT rate, liability standards, guild policy) should generate Tiebout-style sorting: agents move to compacts whose policy mix best matches their preferences. This validates the jurisdictional competition mechanism.

**P7 — Crisis Resilience.** Under exogenous shocks (natural disaster, mass tort, financial crisis), the system should:
- Absorb small shocks without cascading failure
- Show nonlinear amplification beyond some threshold (tipping point)
- Recover to a new equilibrium (not diverge)

### 7.3 Test Configuration

```
Environment: Multi-compact (N_compacts = 3–5), full agent society
- N_agents = 1000–2000 (scaled)
- All mechanics active: LVT, Harberger, Insurance, Courts, Guilds, Fraud Prevention, Dividend
- Compact heterogeneity: different LVT rates, liability standards, guild policies
- Exogenous events enabled (from Event Model): natural disaster, mass tort, tech disruption
Duration: T=1000 ticks (baseline), T=2000 ticks (shock tests)
Sample size: N=500 Monte Carlo runs across parameter grid
```

### 7.4 Acceptance Criteria — Integrated System

#### 7.4.1 Business Cycle & Leverage (P1)

| Criterion | Metric | Threshold | Tier |
|-----------|--------|-----------|------|
| Cyclicality | GDP autocorrelation at lag 1–5 | Must be positive (persistence) | T2 |
| Leverage amplification | Correlation(debt/GDP, GDP volatility) | Positive (more leverage → more volatility) | T2 |
| Recovery shape | GDP after contraction: V-shaped vs U-shaped vs L-shaped | Must produce U-shaped or V-shaped (not permanent divergence) | T2 |
| Inventory / investment co-movement | Correlation(investment, GDP) | ≥ 0.5 (pro-cyclical investment) | T2 |

#### 7.4.2 Inequality Dynamics (P2)

| Criterion | Metric | Threshold | Tier |
|-----------|--------|-----------|------|
| Baseline Gini (market income) | Gini before LVT/dividend | ∈ [0.40, 0.60] | T2 |
| Post-fiscal Gini | Gini after LVT + dividend | ∈ [0.30, 0.48] | T2 |
| Top 10% share | Share of total wealth held by top 10% | ∈ [30%, 60%] | T2 |
| Poverty floor | Bottom decile consumption / median consumption | ≥ 0.40 (dividend provides floor) | T2 |

#### 7.4.3 Tax-Transfer Incidence (P3)

| Criterion | Metric | Threshold | Tier |
|-----------|--------|-----------|------|
| Net fiscal progressivity | Net_transfer_quintile1 / Net_tax_quintile5 | Quintile 1 positive, Quintile 5 negative | T1 |
| Effective LVT burden rate | LVT_paid / income, by income decile | Must be approximately flat or slightly regressive (land holdings correlated with income) | T1 |
| Dividend replacement rate | Dividend / median consumption | ∈ [0.05, 0.30] (significant but not dominant) | T1 |

#### 7.4.4 Insurance-Legal Feedback (P4)

| Criterion | Metric | Threshold | Tier |
|-----------|--------|-----------|------|
| Equilibrium stability | Coefficient of variation of premium rate (last 500 ticks) | CV ≤ 0.15 | T2 |
| Liability-insurance correlation | Correlation(liability_standard, insurance_uptake) | Positive | T1 |
| Court-insurance correlation | Correlation(caseload, premium_rate) | Positive (more litigation → higher premiums) | T1 |
| No explosive loop | Insurance premia / GDP | Must remain bounded (< 0.20) | T1 |

#### 7.4.5 Harberger-LVT-Dividend Loop (P5)

| Criterion | Metric | Threshold | Tier |
|-----------|--------|-----------|------|
| Land value stability | CV(total_land_value) over last 500 ticks | ≤ 0.15 | T2 |
| Dividend-LVT ratio | Dividend / LVT collected | > 0.70 (net of administrative costs) | T1 |
| Price-rent ratio convergence | Median land price / annual LVT bill | Must converge to stable value (no drift) | T2 |

#### 7.4.6 Compact Competition / Tiebout Sorting (P6)

| Criterion | Metric | Threshold | Tier |
|-----------|--------|-----------|------|
| Sorting by preference | Correlation(agent_tax_preference, compact_tax_rate) | Positive (agents sort to preferred compacts) | T2 |
| Migration responsiveness | Elasticity of net_migration to compact_policy_change | Positive (policies attract/repel) | T2 |
| Policy convergence/divergence | Variance of compact policies over time | Must not collapse to zero (differentiation persists) or explode (runaway) | T2 |
| No race-to-bottom | Minimum LVT rate across compacts | Must be > 0 (no tax competition drives all rates to zero) | T1 |

#### 7.4.7 Crisis Resilience (P7)

| Criterion | Metric | Threshold | Tier |
|-----------|--------|-----------|------|
| Small-shock absorption | GDP change after magnitude-3 shock | |ΔGDP| ≤ 5% (return to baseline within 20 ticks) | T2 |
| Tipping point | Shock magnitude at which recovery time exceeds 100 ticks | Must exist within magnitude 6–9 | T2 |
| Cascading failure | Number of secondary events triggered per primary event | Mean ≤ 2 (no runaway cascades) | T2 |
| Recovery completeness | GDP at t=500 post-shock / baseline GDP at t=0 | ≥ 0.90 (system recovers most lost output) | T2 |
| Inequality during crisis | Gini during crisis / Gini before | If Gini rises, must not exceed 1.5× pre-crisis | T1 |

### 7.5 How to Run the Integrated Test

```python
def run_integrated():
    # Baseline run
    for seed in range(500):
        sim = Simulation(config=Config(
            n_compacts=3,
            n_agents=1500,
            mechanics=['lvt', 'harberger', 'insurance', 'courts', 'guilds',
                       'fraud_prevention', 'dividend', 'tiebout_migration'],
            compact_policies={
                'compact_0': {'lvt_rate': 0.04, 'liability_standard': 'strict', 'guild_policy': 'open'},
                'compact_1': {'lvt_rate': 0.07, 'liability_standard': 'negligence', 'guild_policy': 'restrictive'},
                'compact_2': {'lvt_rate': 0.02, 'liability_standard': 'none', 'guild_policy': 'mixed'},
            },
            events_enabled=False,
            n_ticks=1000
        ))
        sim.run()
        integrated_results['baseline'][seed] = compute_all_metrics(sim)
    
    # Shock runs
    for shock_type in ['natural_disaster', 'mass_tort', 'financial_crisis']:
        for magnitude in range(3, 10):
            for seed in range(100):
                sim = Simulation(config=Config(
                    ..., events=[{'type': shock_type, 'magnitude': magnitude, 'tick': 500}], n_ticks=1500
                ))
                sim.run()
                integrated_results['shocks'][(shock_type, magnitude, seed)] = compute_crisis_metrics(sim)
    
    validate_integrated(integrated_results)
```

### 7.6 Integrated System Failure Interpretation

| Failure Mode | Likely Cause | Remediation |
|-------------|--------------|-------------|
| System diverges (explosive growth or collapse) | Missing stabilizing feedback in LVT-Dividend loop or insurance-legal loop | Add automatic stabilizers: LVT rate adjusts counter-cyclically; insurance reserve requirements |
| Gini outside plausible range | Wealth inequality too low: dividend too generous; too high: LVT too low or absent | Calibrate LVT rate and dividend share to match empirical fiscal incidence studies |
| No Tiebout sorting | Migration costs too high or policy differences too small | Reduce migration friction or widen policy differences across compacts |
| Crisis causes permanent divergence (no recovery) | No recovery mechanism; insurance and court systems cannot restructure | Add bankruptcy/reorganization mechanism; ensure insurers can recapitalize |
| Harvester-LVT-Dividend loop oscillates | Time lags in valuation adjustment create phase delays | Add smoothing (moving average of land values for LVT calculation) |

---

## 8. Validation Execution Protocol

### 8.1 Pre-Validation Checklist

Every validation run must pass this checklist before execution:

- [ ] Validation plan recorded (parameters, thresholds, seeds, number of runs)
- [ ] Random seed range fixed and logged (for reproducibility)
- [ ] All code changes committed (git diff clean or documented)
- [ ] Single-mechanic tests can run independently (no cross-contamination from other mechanics)
- [ ] Output metrics defined and instrumented in simulation code
- [ ] Verification: is the mechanic's code path exercised in isolation? (Coverage check)

### 8.2 Validation Lifecycle

```
         ┌──────────────────────────────┐
         │   Pre-registration (plan.md)  │
         └───────────┬──────────────────┘
                     │
         ┌───────────▼──────────────────┐
         │   Stage V1–V9 (isolated)     │
         │   Tier T1 → all must pass    │
         │   Tier T2 → ≥80% must pass   │
         └───────────┬──────────────────┘
                     │
         ┌───────────▼──────────────────┐
         │   Decision Gate (per stage)  │
         │   Pass → mark complete       │
         │   Fail → log, fix, retest    │
         │   [See tasks.md Risk Register]│
         └───────────┬──────────────────┘
                     │
         ┌───────────▼──────────────────┐
         │   Integrated Validation      │
         │   All T1 + T2 criteria       │
         │   T3 pattern validation      │
         └───────────┬──────────────────┘
                     │
         ┌───────────▼──────────────────┐
         │   Final Decision Gate        │
         │   All pass → system ready    │
         │   Any fail → deviation log   │
         └──────────────────────────────┘
```

### 8.3 Decision Gate Protocol

Per the triple-loop architecture, every gate follows this format:

```
=== DECISION GATE ===
Context: <what was tested, what happened>
Fork options:
  A) Accept: criteria met, proceed
  B) Retest: adjust parameters, re-run
  C) Deviate: document known tension, proceed with caveat
  D) Reject: mechanic fails fundamentally, redesign required
Critic decision: <chosen fork + justification>
```

### 8.4 Failure Escalation

| Condition | Action |
|-----------|--------|
| T1 criterion fails | Mechanic redesign required (D) |
| T2 criterion fails, N failures < 20% | Adjust calibration, re-run (B) |
| T2 criterion fails, N failures ≥ 20% | Mechanic redesign required (D) |
| T3 pattern fails but no T1/T2 failure | Document as "Known Tension" (C), may indicate emergent misspecification |
| T3 + T1/T2 fail simultaneously | System architecture review required |

---

## 9. Regression Testing & CI Integration

### 9.1 Continuous Validation

Every code change that touches a core mechanic MUST re-run that mechanic's validation suite. The CI pipeline stages are:

```
pre-commit: lint, type-check    [fast, <30s]
├── commit: unit tests          [<2min]
├── PR: V1–V4 validation suite  [<15min, 10 seeds each]
└── nightly: full validation    [<60min, 100 seeds each]
    ├── V1–V9 (all variations)
    ├── Integrated (baseline)
    └── Integrated (shocks)
```

### 9.2 Validation Artifact Storage

Each validation run produces:
- `validation_run_{stage}_{timestamp}.json` — full metrics dump
- `validation_run_{stage}_{timestamp}.plot.*.png` — key diagnostic plots
- `validation_summary_{stage}_{timestamp}.md` — pass/fail summary with thresholds

Artifacts stored in: `./simulation/validation_artifacts/`

### 9.3 Regression Alerting

If a previously-passing criterion fails after a code change, the CI pipeline MUST:

1. Block the PR/merge
2. Log the regression in `tasks.md` Deviation Log
3. Identify the specific commit and line changes that likely caused the regression
4. Require a Decision Gate to proceed

---

## 10. Appendix: Common Parameter Templates

### 10.1 Agent Utility Function (Baseline)

```python
U(consumption, leisure, honesty) = (
    (consumption ** (1 - γ)) / (1 - γ)  # CRRA consumption utility
    + α * (leisure ** β)                 # Leisure preference
    - θ_effective * D_exploit            # Honesty cost of exploitation
)
```

Default parameters: γ=1.5 (moderate risk aversion), α=0.3, β=0.8, θ ∈ [0,1] uniform.

### 10.2 Simulation Tick Structure

```python
def tick():
    # Phase 1: Production & labor market
    businesses.produce()
    workers.labor_supply_decision()
    labor_market.clear()
    
    # Phase 2: Property & LVT
    harberger.update_declarations()
    lvt.collect()
    harberger.forced_sales()
    
    # Phase 3: Insurance
    accidents.happen()
    insurers.collect_premiums()
    insurers.pay_claims()
    
    # Phase 4: Legal
    courts.process_filings()
    courts.adjudicate()
    courts.enforce_judgments()
    
    # Phase 5: Fiscal
    dividend.distribute()
    compact.update_budget()
    
    # Phase 6: Migration & sorting
    agents.evaluate_compact_satisfaction()
    agents.consider_migration()
```

### 10.3 Default Validation Parameters

| Parameter | V1 | V2 | V3 | V4 | Integrated |
|-----------|----|----|----|----|------------|
| N agents | 1000 | 550 | 700 | 500 | 1500 |
| N ticks | 200 | 500 | 500 | 1000 | 1000 |
| N Monte Carlo seeds | 50 | 100 | 100 | 100 | 500 |
| Tolerance for T1 | Sign + order-of-magnitude | Same | Same | Same | Same |
| Tolerance for T2 | 95% CI bootstrap | 95% CI | 95% CI | 95% CI | 95% CI |
| Acceptance threshold (T1 pass rate) | 100% | 100% | 100% | 100% | 100% |
| Acceptance threshold (T2 pass rate) | — | 80% | 80% | 80% | 80% |

---

> **Document Version:** 1.0  
> **Last Updated:** 2026-05-31  
> **Next Review:** After any core mechanic change  
> **Maintainer:** Simulation Architecture Team
