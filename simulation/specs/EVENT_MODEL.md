# Event & Stress Model Specification

> **Revision:** 1.0  
> **Author:** Simulation Architecture Team  
> **Context:** Liability State simulation — systemic resilience testing  
> **Domain:** Event-driven stress testing of a liability-based political economy

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Event Taxonomy](#2-event-taxonomy)
3. [Event Definitions](#3-event-definitions)
   - [3.1 Natural Disaster](#31-natural-disaster)
   - [3.2 Foreign Invasion](#32-foreign-invasion)
   - [3.3 Mass Tort](#33-mass-tort)
   - [3.4 Technology Disruption](#34-technology-disruption)
   - [3.5 Insurance Market Failure](#35-insurance-market-failure)
   - [3.6 Guild Scandal](#36-guild-scandal)
   - [3.7 Compact Secession](#37-compact-secession)
   - [3.8 Pandemic](#38-pandemic)
   - [3.9 Population Shock](#39-population-shock)
   - [3.10 Class Action](#310-class-action)
   - [3.11 Financial Crisis](#311-financial-crisis)
4. [Recovery Function Library](#4-recovery-function-library)
5. [Cascading Failure System](#5-cascading-failure-system)
6. [Event Interaction Matrix](#6-event-interaction-matrix)
7. [Simulation Integration](#7-simulation-integration)

---

## 1. Architecture Overview

The Event & Stress Model provides the exogenous and endogenous shock mechanisms that stress-test the Liability State simulation. Events are classified along three axes:

| Axis | Values | Description |
|------|--------|-------------|
| **Origin** | External / Internal | Whether the event originates outside or inside the compact system |
| **Nature** | Natural / Human / Systemic | Root causal category |
| **Trigger** | Timed / Probabilistic / Conditional | How the event is activated in simulation time |
| **Recovery** | Linear / Exponential / Market-Driven / Permanent | The shape of healing once the event is resolved |

### Event Lifecycle

```
Trigger ──> Onset ──> Ramp (optional) ──> Peak ──> Plateau (optional) ──> Recovery ──> Resolved
```

Each phase occupies a configurable number of simulation ticks. Events may be interrupted, amplified, or truncated by cascading interactions ([§5](#5-cascading-failure-system)).

### Shared Event Interface (Pseudocode)

```
Event {
  id: string
  name: string
  type: EventType
  origin: OriginClass
  trigger: TriggerCondition
  magnitude: float        // 0.0–10.0 scale
  target: TargetSpec      // which subsystems are affected
  duration: DurationSpec  // onset, peak, recovery tick counts
  effects: Effect[]       // state deltas applied per tick
  recovery: RecoveryFunction
  cascade: CascadeMap     // which secondary events this can trigger
}
```

---

## 2. Event Taxonomy

```
EVENT TAXONOMY
│
├── EXTERNAL (exogenous shocks)
│   ├── Natural Disaster        [earthquake, hurricane, flood, wildfire, volcanic]
│   ├── Foreign Invasion        [conventional, asymmetric, economic warfare]
│   ├── Technology Disruption   [AI displacement, infrastructure failure, cyber]
│   └── Pandemic                [viral, bacterial, chronic environmental]
│
├── INTERNAL (endogenous failures)
│   ├── Mass Tort               [toxic exposure, product liability, malpractice]
│   ├── Insurance Market Failure [insolvency cascade, premium spiral, gap]
│   ├── Guild Scandal           [corruption, credential fraud, accreditation crisis]
│   ├── Compact Secession       [territorial exit, functional defection]
│   ├── Population Shock        [baby bust, mass emigration, refugee influx]
│   ├── Class Action            [systemic liability suit, reparations judgment]
│   └── Financial Crisis        [credit freeze, currency collapse, debt spiral]
│
└── SYSTEMIC (emergent from event interactions)
    └── Cascading Failure       [triggered by any event's cascade map]
```

---

## 3. Event Definitions

### 3.1 Natural Disaster

| Field | Value |
|-------|-------|
| **Origin** | External |
| **Nature** | Natural |
| **Symbol** | `NAT_DISASTER` |

#### Trigger Conditions

| Trigger Type | Configuration |
|-------------|---------------|
| **Timed** | Fixed date events (e.g., seasonally recurring: "Hurricane Season Year 3") |
| **Probabilistic** | Base probability: `P = 0.02 + (0.01 × years_elapsed)` per simulation year; regional frequency modifiers (seismic zones, hurricane corridors) multiply by 1.5–3.0× |
| **Conditional** | Triggered by cascading failure when Infrastructure Degradation > 0.7 (dam failures, industrial accidents) |

#### Parameters

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `magnitude` | float | 1.0–10.0 | Richter/saffir-simpson analogue. >6.0 is catastrophic |
| `target_region` | string set | [compact territory IDs] | Which geographic regions are affected |
| `disaster_type` | enum | earthquake / hurricane / flood / wildfire / volcanic | Determines damage profile |
| `duration` | int ticks | 1–90 | How long the active disaster lasts |
| `recovery_duration` | int ticks | 10–365 | How long recovery takes after disaster ends |
| `aftershock_count` | int | 0–20 | Secondary events during recovery (earthquake only) |

#### Effects on System State

Applied each simulation tick during `[onset_tick, onset_tick + duration]`:

| Effect | Target | Magnitude Scaling | Description |
|--------|--------|-------------------|-------------|
| `infrastructure_damage` | target_region | `+0.15 × magnitude` per tick (capped at 1.0) | Roads, power, water destroyed |
| `population_displacement` | target_region | `+0.08 × magnitude` per tick | People flee affected area |
| `liability_claims` | InsurancePool | `+0.10 × magnitude` per tick | Emergency claims flood system |
| `tax_revenue` | Compact Treasury | `−0.05 × magnitude` per tick | Economic disruption reduces income |
| `guild_productivity` | Guild system | `−0.12 × magnitude` per tick | Workers can't operate |
| `mortality` | Population | `+0.003 × magnitude` per tick | Direct deaths |

#### Recovery Functions

| Aspect | Recovery Shape | Parameters |
|--------|---------------|------------|
| **Infrastructure** | **Exponential** (accelerated reconstruction) | `R(t) = 1 − e^{−λ t}`, λ = 0.02 × `compact_resilience_score` |
| **Population Return** | **Linear** | `R(t) = min(1.0, t / recovery_duration)` |
| **Liability Overhang** | **Market-Driven** | Decays only when `InsurancePool.reserves > 0.3 × total_liabilities` |
| **Permanent Scarring** | **Permanent** (floor) | `infrastructure_damage` never drops below 0.05 × magnitude — residual fragility |

### 3.2 Foreign Invasion

| Field | Value |
|-------|-------|
| **Origin** | External |
| **Nature** | Human |
| **Symbol** | `FOREIGN_INVASION` |

#### Trigger Conditions

| Trigger Type | Configuration |
|-------------|---------------|
| **Timed** | — |
| **Probabilistic** | `P = 0.005 × compact_weakness_score` per year, where `compact_weakness_score` = (1 − `military_readiness`) × (1 − `compact_cohesion`) |
| **Conditional** | Fires when `defense_liability_ratio > 2.0` AND `compact_cohesion < 0.4` (perceived vulnerability threshold) |

#### Parameters

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `magnitude` | float | 1.0–10.0 | Invasion force size relative to defender |
| `invasion_type` | enum | conventional / asymmetric / economic_warfare | Determines damage vector |
| `target_region` | string set | border territories | Primary invasion corridor |
| `aggressor_strength` | float | 0.3–2.0 | Relative to defender (2.0 = overwhelming force) |
| `duration` | int ticks | 30–180 | Active conflict phase |

#### Effects on System State

| Effect | Target | Scaling | Description |
|--------|--------|---------|-------------|
| `military_readiness` | Compact Defense | `−0.20 × magnitude` per tick | Attrition |
| `territory_loss` | target_region | Binary: occupied if `defense < offense` | Land seized |
| `infrastructure_destruction` | Occupied + contested | `+0.25 × magnitude` per tick | Scorched-earth / collateral |
| `population_refugee_flow` | Non-occupied | `+0.15 × magnitude` per tick | Internal displacement |
| `compact_cohesion` | Compact Council | `−0.05 × magnitude` per tick | Fracturing under pressure |
| `guild_military_contracts` | Defense guilds | `+0.30 × magnitude` (surge) | War economy spike |
| `liability_claims` | InsurancePool | `+0.20 × magnitude` per tick | War damage claims |
| `confidence_index` | Market system | `−0.10 × magnitude` per tick | Investor panic |

#### Recovery Functions

| Aspect | Recovery Shape | Parameters |
|--------|---------------|------------|
| **Territory** | **Conditional** | Liberated only if counter-offensive succeeds (simulated as conditional event check every 30 ticks) |
| **Infrastructure** | **Exponential** | λ = 0.01 × `post_war_aid_level` (slow without external aid) |
| **Compact Cohesion** | **Linear** | Recovers over 3× the conflict duration (deep trust damage is slow to heal) |
| **Military Readiness** | **Exponential** | λ = 0.03, can overshoot pre-war levels via "war mobilization" bonus |
| **Psychological Scar** | **Permanent** | `invasion_memory` variable persists; future `compact_weakness_score` floor raised by 0.05 × magnitude |

### 3.3 Mass Tort

| Field | Value |
|-------|-------|
| **Origin** | Internal |
| **Nature** | Human / Systemic |
| **Symbol** | `MASS_TORT` |

#### Trigger Conditions

| Trigger Type | Configuration |
|-------------|---------------|
| **Timed** | — |
| **Probabilistic** | `P = 0.01 × (industrial_density × regulation_violation_index)` per year |
| **Conditional** | Fires when any guild's `safety_compliance_score < 0.3` for 3+ consecutive ticks (latent mass tort becomes active) |

#### Parameters

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `magnitude` | float | 1.0–10.0 | Number of claimants (millions-equivalent) |
| `tort_type` | enum | toxic_exposure / product_liability / medical_malpractice / environmental | Determines liability class |
| `target_guilds` | string set | Which guild(s) are liable | Affects guild liability pools |
| `latency` | int ticks | 10–365 | Time between exposure and claim filing (environmental torts have longer latency) |
| `duration` | int ticks | 60–500 | Claim adjudication period |

#### Effects on System State

| Effect | Target | Scaling | Description |
|--------|--------|---------|-------------|
| `guild_liability` | target_guilds | `+0.30 × magnitude` per tick | Claims accumulate |
| `guild_premium` | target_guilds | `+0.15 × magnitude` per tick | Insurance premiums spike |
| `guild_solvency_risk` | target_guilds | `+0.20 × magnitude` per tick | Risk of guild bankruptcy |
| `public_trust` | Compact-wide | `−0.05 × magnitude` | Erosion of institutional trust |
| `compact_legal_burden` | Judicial system | `+0.10 × magnitude` per tick | Court system overload |
| `regulation_strictness` | Compact regulatory | `+0.05 × magnitude` per tick | Policy response (increases slowly) |

#### Recovery Functions

| Aspect | Recovery Shape | Parameters |
|--------|---------------|------------|
| **Guild Liability** | **Linear** (judgment payments) | `R(t) = max(0, initial − payment_rate × t)`, payment_rate depends on guild solvency |
| **Guild Premium** | **Market-Driven** | Returns to baseline only when `guild_safety_compliance > 0.7` AND `claims_resolved > 0.9` |
| **Public Trust** | **Exponential** | λ = 0.01 × `reform_credibility` (trust rebuilds slowly even with reforms) |
| **Regulation** | **Permanent** | New regulations never fully repealed; `regulation_strictness` baseline permanently raised by 0.02 × magnitude |

### 3.4 Technology Disruption

| Field | Value |
|-------|-------|
| **Origin** | External / Internal |
| **Nature** | Human / Systemic |
| **Symbol** | `TECH_DISRUPTION` |

#### Trigger Conditions

| Trigger Type | Configuration |
|-------------|---------------|
| **Timed** | Fires on fixed schedule proportional to simulation `tech_progress_rate` (every 5–15 years) |
| **Probabilistic** | `P = 0.10 × tech_progress_rate` per year (breakthrough probability) |
| **Conditional** | Fires when a guild's `automation_resistance > 0.8` AND `tech_investment > 0.6` (disruptive innovation bypasses entrenched guilds) |

#### Parameters

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `magnitude` | float | 1.0–10.0 | Labor displacement fraction |
| `disruption_type` | enum | ai_automation / infrastructure_failure / cyber_attack / energy_transition | Determines which guilds are impacted |
| `target_guilds` | string set | Which guilds face obsolescence |
| `adoption_rate` | float | 0.1–0.9 | How fast the new technology replaces old |
| `duration` | int ticks | 60–730 | Transition period |

#### Effects on System State

| Effect | Target | Scaling | Description |
|--------|--------|---------|-------------|
| `guild_membership` | target_guilds | `−0.20 × magnitude` per tick | Labor displacement |
| `guild_productivity` | target_guilds | Initial `−0.15 × magnitude` then `+0.25 × magnitude` (J-curve) | Efficiency gains after adoption |
| `unemployment` | Compact-wide | `+0.08 × magnitude` per tick | Structural unemployment |
| `retraining_demand` | Education guild | `+0.25 × magnitude` per tick | Surge in demand for reskilling |
| `tax_revenue` | Compact Treasury | `−0.03 × magnitude` per tick (temporary) | Transition friction |
| `innovation_index` | Compact-wide | `+0.15 × magnitude` per tick | Long-term tech base improves |
| `inequality` | Compact-wide | `+0.06 × magnitude` | Skill-biased tech change widens gaps |

#### Recovery Functions

| Aspect | Recovery Shape | Parameters |
|--------|---------------|------------|
| **Guild Employment** | **Market-Driven** | New equilibrium forms when `retrained_workers / displaced_workers > 0.7`; some guilds may never recover full employment (permanent structural shift) |
| **Productivity** | **Exponential** | J-curve: dips 20–40 ticks then `R(t) = 1 + α(1 − e^{−λ t})` where α = magnitude × 0.3 (productivity gains overshoot pre-disruption level) |
| **Inequality** | **Permanent** (floor) | Inequality baseline permanently raised by 0.02 × magnitude unless redistributive policy enacted |
| **Innovation Index** | **Exponential** | λ = 0.01 × `tech_absorptive_capacity`; innovation remains elevated permanently |

### 3.5 Insurance Market Failure

| Field | Value |
|-------|-------|
| **Origin** | Internal |
| **Nature** | Systemic |
| **Symbol** | `INSURANCE_FAILURE` |

#### Trigger Conditions

| Trigger Type | Configuration |
|-------------|---------------|
| **Timed** | — |
| **Probabilistic** | `P = 0.03 × (1 − regulation_quality) × liability_exposure_ratio` per year |
| **Conditional** | Fires when `InsurancePool.solvency_ratio < 0.25` AND 3+ concurrent major liability events active (systemic overload) |

#### Parameters

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `magnitude` | float | 1.0–10.0 | Severity of market failure (insolvency depth) |
| `failure_type` | enum | insolvency_cascade / premium_spiral / coverage_gap / adverse_selection_death_spiral | Determines mechanism |
| `target_pools` | string set | Which insurance segments fail (general, guild, disaster, health) |
| `duration` | int ticks | 30–365 | Acute failure period |

#### Effects on System State

| Effect | Target | Scaling | Description |
|--------|--------|---------|-------------|
| `insurance_solvency` | target_pools | `−0.25 × magnitude` per tick | Collapse of reserves |
| `insurance_premium` | Compact-wide | `+0.20 × magnitude` per tick | Premiums skyrocket |
| `uninsured_rate` | Compact-wide | `+0.10 × magnitude` per tick | Growing coverage gap |
| `liability_claims_unpaid` | System-wide | `+0.15 × magnitude` per tick | Uncompensated losses |
| `guild_solvency_risk` | All guilds | `+0.08 × magnitude` per tick | Guilds can't transfer risk |
| `public_trust` | Compact-wide | `−0.06 × magnitude` per tick | Confidence collapse |
| `compact_bailout_cost` | Compact Treasury | `+0.20 × magnitude` per tick (if bailout policy active) | Fiscal cost of rescue |

#### Recovery Functions

| Aspect | Recovery Shape | Parameters |
|--------|---------------|------------|
| **Solvency** | **Linear** (capital injection / premium normalization) | `R(t) = min(1.0, t / (duration × 2))` with floor at 0.1 if no regulatory reform |
| **Premium** | **Market-Driven** | Returns to equilibrium only when `solvency_ratio > 0.5` AND `new_entrants > 0` |
| **Uninsured Rate** | **Exponential** | λ = 0.01 × `compact_insurance_mandate_strength` |
| **Systemic Trust** | **Exponential** | λ = 0.005 (very slow); trust damage is severe and persistent |
| **Permanent Scar** | **Permanent** | `insurance_resilience_score` reduced by 0.05 × magnitude permanently; future failures more likely |

### 3.6 Guild Scandal

| Field | Value |
|-------|-------|
| **Origin** | Internal |
| **Nature** | Human |
| **Symbol** | `GUILD_SCANDAL` |

#### Trigger Conditions

| Trigger Type | Configuration |
|-------------|---------------|
| **Timed** | — |
| **Probabilistic** | `P = 0.02 × guild_corruption_index` per year per guild (corruption_index = 1 − governance_score) |
| **Conditional** | Fires when `guild_internal_oversight < 0.2` for 5+ consecutive ticks (failure of self-regulation) |

#### Parameters

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `magnitude` | float | 1.0–10.0 | Severity of scandal (embezzlement level, fraud scale) |
| `scandal_type` | enum | embezzlement / credential_fraud / accreditation_crisis / collusion / bribery | Determines legal and reputational effects |
| `target_guild` | string | Single guild | Which guild is implicated |
| `duration` | int ticks | 30–180 | Investigative / adjudication phase |

#### Effects on System State

| Effect | Target | Scaling | Description |
|--------|--------|---------|-------------|
| `guild_trust` | target_guild | `−0.30 × magnitude` per tick | Reputation collapse |
| `guild_membership` | target_guild | `−0.10 × magnitude` per tick | Members leave |
| `guild_revenue` | target_guild | `−0.20 × magnitude` per tick | Lost business |
| `compact_oversight_demand` | Compact regulatory | `+0.15 × magnitude` per tick | Political pressure to regulate guilds |
| `compact_cohesion` | Compact-wide | `−0.02 × magnitude` per tick | Spillover distrust to entire compact |
| `public_trust` | Compact-wide | `−0.04 × magnitude` per tick | Trust erosion |

#### Recovery Functions

| Aspect | Recovery Shape | Parameters |
|--------|---------------|------------|
| **Guild Trust** | **Exponential** | λ = 0.01 × `governance_reform_score`; takes years even with best reforms |
| **Guild Membership** | **Market-Driven** | Returns when `guild_trust > 0.5` AND `guild_value_proposition > baseline` |
| **Guild Revenue** | **Linear** (slow) | `R(t) = min(1.0, t / (duration × 3))` |
| **Regulatory Oversight** | **Permanent** | Oversight level never drops below `max(pre_scandal, 0.3)` — reform legacy |
| **Public Trust (spillover)** | **Exponential** | λ = 0.008 (decades-long recovery) |

### 3.7 Compact Secession

| Field | Value |
|-------|-------|
| **Origin** | Internal |
| **Nature** | Human / Systemic |
| **Symbol** | `COMPACT_SECESSION` |

#### Trigger Conditions

| Trigger Type | Configuration |
|-------------|---------------|
| **Timed** | — |
| **Probabilistic** | `P = 0.005 × (1 − compact_cohesion) × (economic_disparity_index)` per year per member state |
| **Conditional** | Fires when any member's `net_benefit_from_compact < −0.3` AND `secession_support > 0.6` for 10+ consecutive ticks |

#### Parameters

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `magnitude` | float | 1.0–10.0 | Economic/political size of seceding member as fraction of compact |
| `secession_type` | enum | territorial_exit / functional_defection / partial_withdrawal | Full exit or partial defection |
| `target_member` | string set | Which member(s) secede |
| `duration` | int ticks | 60–365 | Negotiation / transition period |
| `hostile_secession` | bool | true/false | Whether the exit is amicable or contested |

#### Effects on System State

| Effect | Target | Scaling | Description |
|--------|--------|---------|-------------|
| `compact_cohesion` | Compact-wide | `−0.15 × magnitude` per tick | Domino effect — remaining members question commitment |
| `compact_tax_revenue` | Compact Treasury | `−0.20 × magnitude` per tick (permanent loss) | Lost tax base |
| `compact_military_readiness` | Defense | `−0.15 × magnitude` per tick | Lost troop contributions |
| `trade_flow` | Compact-wide | `−0.20 × magnitude` per tick | Disrupted internal market |
| `insurance_pool_reserves` | InsurancePool | `−0.10 × magnitude` per tick | Lost premium contributions |
| `secession_probability_others` | Remaining members | Multiplied by 1.5× | Contagion risk |
| `guild_disruption` | Cross-border guilds | `−0.12 × magnitude` per tick | Guilds with operations in seceded region lose coordination |

#### Recovery Functions

| Aspect | Recovery Shape | Parameters |
|--------|---------------|------------|
| **Compact Cohesion** | **Linear** (very slow) | `R(t) = min(1.0, t / 1000)` — cohesion takes decades to rebuild |
| **Tax Revenue** | **Permanent** | Lost unless new members join; baseline revenue permanently reduced |
| **Trade Flow** | **Market-Driven** | New trade agreements may partially compensate; never exceeds pre-secession levels |
| **Secession Contagion** | **Conditional** | Only stops when `compact_cohesion > 0.6` AND `reform_program_active = true` |
| **Insurance Pool** | **Linear** | New member contributions or premium increases fill gap over time |

### 3.8 Pandemic

| Field | Value |
|-------|-------|
| **Origin** | External |
| **Nature** | Natural |
| **Symbol** | `PANDEMIC` |

#### Trigger Conditions

| Trigger Type | Configuration |
|-------------|---------------|
| **Timed** | — |
| **Probabilistic** | `P = 0.02 × (1 − health_surveillance_score)` per year; cumulative risk increases with population density and trade openness |
| **Conditional** | Fires when local outbreak detected AND `containment_score < 0.4` (simulation tests whether compact can contain) |

#### Parameters

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `magnitude` | float | 1.0–10.0 | Infection rate (R0 analogue: 1.0–10.0) |
| `lethality` | float | 0.001–0.10 | Infection fatality rate |
| `strain_type` | enum | novel_virus / antimicrobial_resistant / chronic_environmental | Determines mutation profile |
| `target_region` | string set | All regions (spreads over time) |
| `duration` | int ticks | 90–730 | Active pandemic phase |
| `mutation_rate` | float | 0.0–0.1 | Probability of new strain emerging per tick |

#### Effects on System State

| Effect | Target | Scaling | Description |
|--------|--------|---------|-------------|
| `mortality` | Population | `+0.004 × magnitude × lethality × 100` per tick | Deaths |
| `labor_force` | Guild system | `−0.10 × magnitude` per tick | Sick workers / lockdowns |
| `healthcare_capacity` | Health guild | Overload: `capacity − demand` goes negative by `0.20 × magnitude` | ICU / hospital crisis |
| `compact_revenue` | Compact Treasury | `−0.05 × magnitude` per tick | Economic shutdown |
| `public_trust` | Compact-wide | Depends: `+0.02 × magnitude` if response effective, `−0.05 × magnitude` if not | Trust can increase or decrease |
| `guild_productivity` | All guilds | `−0.08 × magnitude` per tick | Supply chain disruption |
| `inequality` | Compact-wide | `+0.04 × magnitude` | Disproportionate impact on lower tiers |
| `debt_level` | Compact Treasury | `+0.10 × magnitude` per tick | Emergency borrowing |

#### Recovery Functions

| Aspect | Recovery Shape | Parameters |
|--------|---------------|------------|
| **Population** | **Linear** (births + immigration) | Recovers over 3–10× pandemic duration depending on lethality |
| **Labor Force** | **Exponential** | λ = 0.02 × `economic_stimulus_level` |
| **Healthcare Capacity** | **Exponential** | λ = 0.03 × `health_investment`; may permanently increase if investment sustained |
| **Public Debt** | **Linear** | `R(t) = max(0, debt_level − surplus_rate × t)` |
| **Inequality** | **Permanent** (floor) | Inequality baseline permanently raised by 0.01 × magnitude × lethality |
| **Public Trust** | **Hysteresis** | Settles at `max(pre_trust − 0.03 × magnitude, 0.5` if response was poor) OR `min(pre_trust + 0.02 × magnitude, 0.9` if response was good) |
| **Immunity Legacy** | **Permanent** | Population immunity reduces future pandemic magnitude by 0.3× for related strains |

### 3.9 Population Shock

| Field | Value |
|-------|-------|
| **Origin** | External / Internal |
| **Nature** | Human |
| **Symbol** | `POPULATION_SHOCK` |

#### Trigger Conditions

| Trigger Type | Configuration |
|-------------|---------------|
| **Timed** | Structural demographic shifts at fixed intervals (e.g., baby bust every 20–30 simulation years) |
| **Probabilistic** | `P = 0.01 × (1 − quality_of_life_index)` per year (emigration driver) |
| **Conditional** | Fires when `compact_economic_opportunity < refugee_pushed_regions_opportunity` for 5+ ticks (mass immigration); fires when `birth_rate < 1.5` for 10+ consecutive years (baby bust) |

#### Parameters

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `magnitude` | float | 1.0–10.0 | Population change fraction |
| `shock_type` | enum | baby_bust / baby_boom / mass_emigration / refugee_influx / demographic_aging | Determines age structure impact |
| `target_region` | string set | Which regions |
| `duration` | int ticks | 180–1095 | Transition period |
| `age_profile` | float[5] | [0–18, 19–35, 36–55, 56–75, 76+] distribution | Age structure of shock |

#### Effects on System State

| Effect | Target | Scaling | Description |
|--------|--------|---------|-------------|
| `total_population` | target_region | `±0.05 × magnitude` per tick | Increase or decrease |
| `dependency_ratio` | Compact-wide | Depends on age_profile | More elderly or young = higher dependency |
| `labor_force` | Guild system | `±0.06 × magnitude` per tick | Changes in working-age population |
| `housing_demand` | target_region | `±0.08 × magnitude` per tick | Housing market pressure |
| `social_service_cost` | Compact Treasury | `+0.04 × magnitude × dependency_ratio` per tick | Pensions, healthcare, education |
| `tax_revenue` | Compact Treasury | `±0.03 × magnitude` per tick | Swings with labor force |
| `guild_membership` | Targeted guilds | `±0.05 × magnitude` per tick | Matching workforce changes |
| `compact_cohesion` | Compact-wide | `−0.01 × magnitude` (cultural friction from rapid change) | Tension from demographic shifts |

#### Recovery Functions

| Aspect | Recovery Shape | Parameters |
|--------|---------------|------------|
| **Population** | **Permanent** (new baseline) | Population settles at new level; birth rates adapt slowly over 5–10 ticks |
| **Dependency Ratio** | **Linear** | Ages through as demographic bulge moves; full recovery in 20–40 ticks |
| **Labor Force** | **Market-Driven** | Adjusts via immigration/emigration and automation adoption |
| **Social Service Cost** | **Exponential** (decays as bulge ages out) | `R(t) = initial × e^{−λ t}` where λ depends on shock_type |
| **Compact Cohesion** | **Linear** | Friction from rapid demographic change heals over 2× the shock duration |

### 3.10 Class Action

| Field | Value |
|-------|-------|
| **Origin** | Internal |
| **Nature** | Human / Systemic |
| **Symbol** | `CLASS_ACTION` |

#### Trigger Conditions

| Trigger Type | Configuration |
|-------------|---------------|
| **Timed** | — |
| **Probabilistic** | `P = 0.008 × (1 − compact_legal_legitimacy) × inequality_index` per year |
| **Conditional** | Fires when `grievance_index > 0.7` for 10+ ticks — where `grievance_index = weighted_sum(inequality, uninsured_rate, liability_uncompensated, trust_deficit)` |

#### Parameters

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `magnitude` | float | 1.0–10.0 | Scale of the class (population fraction) |
| `action_type` | enum | systemic_liability / reparations_claim / civil_rights / contract_violation | Determines legal basis |
| `target_defendants` | string set | Compact, specific guilds, or InsurancePool |
| `duration` | int ticks | 90–730 | Litigation period |
| `success_probability` | float | 0.0–1.0 | Probability of plaintiff victory, calibrated by compact_rule_of_law |

#### Effects on System State

| Effect | Target | Scaling | Description |
|--------|--------|---------|-------------|
| `compact_legal_burden` | Judicial system | `+0.15 × magnitude` per tick | Court overload |
| `compact_liability` | Compact Treasury | If plaintiff wins: `+0.30 × magnitude × success_probability` as lump-sum judgment | Direct fiscal hit |
| `guild_liability` | target_guilds | `+0.20 × magnitude` per tick if guilds are defendants | Secondary liability |
| `guild_premium` | All guilds | `+0.05 × magnitude` per tick | Systemic premium increase |
| `compact_cohesion` | Compact-wide | `−0.03 × magnitude` per tick | Political fracturing |
| `public_trust` | Compact-wide | `+0.04 × magnitude` if victory AND reforms follow, `−0.04 × magnitude` if loss | Trust can go either way |
| `policy_reform_pressure` | Compact legislative | `+0.10 × magnitude` per tick | Momentum for structural change |

#### Recovery Functions

| Aspect | Recovery Shape | Parameters |
|--------|---------------|------------|
| **Judicial Burden** | **Exponential** (case backlog clears) | λ = 0.02 × `judicial_capacity` |
| **Compact Liability** | **Linear** (structured judgment payments) | `R(t) = max(0, judgment − payment_rate × t)`, payment_rate = min(0.1, compact_surplus_ratio) |
| **Guild Premium** | **Market-Driven** | Returns to baseline only when `litigation_environment_score < pre_event_level` |
| **Public Trust** | **Exponential** | λ = 0.01 × `reform_implementation_quality` |
| **Policy** | **Permanent** | New policies (e.g., liability caps, expanded access) permanently alter simulation parameters |

### 3.11 Financial Crisis

| Field | Value |
|-------|-------|
| **Origin** | External / Internal |
| **Nature** | Systemic |
| **Symbol** | `FINANCIAL_CRISIS` |

#### Trigger Conditions

| Trigger Type | Configuration |
|-------------|---------------|
| **Timed** | Financial cycles: crisis probability peaks every 8–12 simulation years (endogenous to asset price cycles) |
| **Probabilistic** | `P = 0.02 × (debt_to_gdp + asset_bubble_index + leverage_ratio − regulation_strictness)` per year — annual crisis probability |
| **Conditional** | Fires when `systemic_leverage > 3.0` AND `market_volatility > 0.7` for 5+ consecutive ticks |

#### Parameters

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `magnitude` | float | 1.0–10.0 | Severity (GDP contraction equivalent) |
| `crisis_type` | enum | credit_freeze / currency_collapse / debt_spiral / asset_bubble_burst / banking_crisis | Determines damage vector |
| `duration` | int ticks | 60–365 | Acute crisis phase |
| `contagion_spread` | float | 0.0–1.0 | How much the crisis spreads to non-financial sectors |
| `policy_response_delay` | int ticks | 5–30 | How quickly the compact can respond |

#### Effects on System State

| Effect | Target | Scaling | Description |
|--------|--------|---------|-------------|
| `compact_revenue` | Compact Treasury | `−0.15 × magnitude` per tick | Tax revenue collapse |
| `compact_debt` | Compact Treasury | `+0.20 × magnitude` per tick | Emergency spending + bailouts |
| `insurance_solvency` | InsurancePool | `−0.15 × magnitude` per tick | Investment losses |
| `guild_revenue` | All guilds | `−0.12 × magnitude` per tick | Demand collapse |
| `guild_solvency_risk` | All guilds | `+0.10 × magnitude` per tick | Bankruptcy wave |
| `unemployment` | Compact-wide | `+0.08 × magnitude` per tick | Job losses |
| `public_trust` | Compact-wide | `−0.06 × magnitude` per tick | Systemic distrust |
| `inequality` | Compact-wide | `+0.05 × magnitude` per tick | Wealth destruction concentrated |
| `compact_cohesion` | Compact-wide | `−0.04 × magnitude` per tick | Political stress |
| `trade_flow` | Compact-wide | `−0.10 × magnitude` per tick | Trade contraction |

#### Recovery Functions

| Aspect | Recovery Shape | Parameters |
|--------|---------------|------------|
| **GDP/Tax Revenue** | **Exponential** (K-shaped — varies by sector) | λ = 0.01 × `stimulus_effectiveness`; recovery may be K-shaped (wealthy recover fast, poor slow) |
| **Insurance Solvency** | **Market-Driven** | Returns when `market_index > 0.8 × pre_crisis` AND `new_premiums_flowing` |
| **Guild Solvency** | **Linear** | `R(t) = min(1.0, t / (duration × 3))` — bankruptcies are resolved slowly |
| **Employment** | **Exponential** (hysteresis risk) | λ = 0.015 × `labor_market_flexibility`; long-term unemployment may become structural |
| **Public Debt** | **Linear** | Reduced via primary surplus; may take decades |
| **Inequality** | **Permanent** (increases baseline) | `inequality_baseline` increased by 0.03 × magnitude permanently |
| **Systemic Regulation** | **Permanent** | New financial regulations permanently reduce future crisis probability by 0.2× and magnitude by 0.1× |
| **Compact Cohesion** | **Exponential** | λ = 0.005 (very slow — political scars last) |

---

## 4. Recovery Function Library

All recovery functions take the form `R(t) → [0, 1]` where `0` = not recovered and `1` = fully recovered. The simulation applies `state = initial_damage × (1 − R(t))`.

### 4.1 Linear Recovery

```
R_linear(t) = min(1.0, t / T)
```

**Use cases:** Debt repayment, population return, structured judgments.  
**Properties:** Predictable, no acceleration, floor at 0.

### 4.2 Exponential Recovery

```
R_exp(t) = 1 − e^{−λ t}
```

**Use cases:** Infrastructure reconstruction, trust rebuilding, healthcare recovery.  
**Parameters:** λ (decay constant) — higher λ = faster recovery. Often modulated by policy variables.  
**Properties:** Fast initial growth, asymptotic approach to full recovery. Never quite reaches 1.0 in finite time — implement with a threshold (e.g., `R > 0.99` = resolved).

### 4.3 Market-Driven Recovery

```
R_market(t) = f(external_state_variables)
```

**Use cases:** Insurance solvency, guild employment equilibrium, premium normalization.  
**Properties:** Non-linear, path-dependent, may stall or reverse if conditions aren't met. Implemented as a state machine:

```
MARKET_DRIVEN RECOVERY STATE MACHINE:
  HALTED   → conditions not met (e.g., reserves too low)
  ACTIVE   → conditions partially met, recovering at rate φ
  CATCH_UP → overshoot recovery when conditions strongly met
  DONE     → resolved
```

### 4.4 Permanent Effect

```
R_permanent(t) = 0  (for all t)
```

**Use cases:** Irreversible damage (extinct guild, seceded territory, baseline inequality shifts, regulatory legacy).  
**Properties:** The system never returns to the pre-event state. A "new normal" emerges with permanently altered parameters.

### 4.5 Hysteresis Recovery

```
R_hysteresis(t) = baseline + Δ × (1 − e^{−λ t})
```

**Use cases:** Public trust after pandemic, compact cohesion after secession.  
**Properties:** System settles at a new equilibrium between pre-event baseline and full recovery. The "scar" is permanent but partial.

### 4.6 Conditional Recovery

```
R_conditional(t) = {
    0.0                    if precondition not met
    R_exp(t − delay)       once precondition satisfied
}
```

**Use cases:** Territorial liberation (requires counter-offensive), guild trust (requires governance reform).  
**Properties:** Recovery is blocked until a system state condition is satisfied. Creates incentive for policy action.

### Recovery Lookup Table

| Event | Infrastructure | Population | Liability | Trust | Revenue | Cohesion | Insurance | Employment | Inequality | Regulation |
|-------|---------------|------------|-----------|-------|---------|----------|-----------|------------|------------|------------|
| **3.1 Natural Disaster** | Exp | Lin | Mkt | — | — | — | — | — | — | — |
| **3.2 Foreign Invasion** | Exp | Cond | — | Perm | — | Lin | — | — | — | — |
| **3.3 Mass Tort** | — | — | Lin | Exp | — | — | — | — | — | Perm |
| **3.4 Tech Disruption** | — | — | — | — | — | — | — | Mkt | Perm | — |
| **3.5 Insurance Failure** | — | — | — | Exp | — | — | Lin | — | — | Perm |
| **3.6 Guild Scandal** | — | — | — | Exp | — | — | — | Mkt | — | Perm |
| **3.7 Compact Secession** | — | — | — | — | Perm | Lin | Lin | — | — | — |
| **3.8 Pandemic** | — | Lin | — | Hys | Lin | — | — | Exp | Perm | — |
| **3.9 Population Shock** | — | Perm | — | — | — | Lin | — | Mkt | — | — |
| **3.10 Class Action** | — | — | Lin | Exp | — | — | — | — | — | Perm |
| **3.11 Financial Crisis** | — | — | — | Exp | Exp | Exp | Mkt | Exp | Perm | Perm |

---

## 5. Cascading Failure System

### 5.1 Theory of Operation

Events do not exist in isolation. When an event reaches certain severity thresholds, it may trigger secondary events — creating cascading failures that compound system stress. The cascade system is modeled as a directed graph with weighted edges.

### 5.2 Cascade Graph

```
NAT_DISASTER ──> INSURANCE_FAILURE (if infrastructure_damage > 0.7)
             ──> POPULATION_SHOCK  (if mortality > threshold)
             ──> FINANCIAL_CRISIS  (if liability_claims > InsurancePool.reserves × 3)

FOREIGN_INVASION ──> COMPACT_SECESSION   (if cohesion < 0.2)
               ──> FINANCIAL_CRISIS      (if war_duration > 120 ticks)
               ──> PANDEMIC              (if refugee_flow × population_density > threshold)

MASS_TORT ──> GUILD_SCANDAL          (if investigations uncover corruption)
          ──> INSURANCE_FAILURE      (if claims > reserves)
          ──> CLASS_ACTION           (if systemic pattern discovered)

TECH_DISRUPTION ──> POPULATION_SHOCK     (if mass unemployment → emigration)
               ──> GUILD_SCANDAL         (if incumbent guilds fraudulently resist transition)
               ──> FINANCIAL_CRISIS      (if asset valuation dislocation > 0.5)

INSURANCE_FAILURE ──> FINANCIAL_CRISIS   (systemic contagion)
                 ──> MASS_TORT           (uncompensated victims organize)
                 ──> CLASS_ACTION        (against compact for regulatory failure)

GUILD_SCANDAL ──> COMPACT_SECESSION  (if guild is critical to compact identity)
             ──> MASS_TORT           (if scandal involves safety fraud)
             ──> CLASS_ACTION        (defrauded members sue)

COMPACT_SECESSION ──> FINANCIAL_CRISIS     (market panic)
                 ──> FOREIGN_INVASION      (perceived weakness)
                 ──> INSURANCE_FAILURE     (pool fragmentation)

PANDEMIC ──> FINANCIAL_CRISIS         (economic shutdown)
         ──> POPULATION_SHOCK         (demographic restructuring)
         ──> INSURANCE_FAILURE        (health insurance collapse)

POPULATION_SHOCK ──> COMPACT_SECESSION    (cultural/political friction)
                ──> FINANCIAL_CRISIS      (asset price dislocation)
                ──> PANDEMIC              (if refugee_influx + poor health surveillance)

CLASS_ACTION ──> COMPACT_SECESSION   (if judgment fractures compact)
             ──> GUILD_SCANDAL       (if discovery reveals guild misconduct)
             ──> FINANCIAL_CRISIS    (if judgment > compact_reserves)

FINANCIAL_CRISIS ──> INSURANCE_FAILURE   (investment losses)
                 ──> COMPACT_SECESSION   (austerity triggers exit)
                 ──> POPULATION_SHOCK   (emigration)
                 ──> GUILD_SCANDAL      (desperation leads to fraud)
```

### 5.3 Cascade Activation Rules

```
interface CascadeCondition {
  source_event: Event
  target_event_type: EventType
  probability: float      // base activation probability
  threshold: {            // condition to check
    variable: string      // system state variable
    operator: '>' | '<' | '>=' | '<='
    value: float
  }
  magnitude_factor: float // target_event.magnitude = source_event.magnitude × this
  delay_ticks: int        // ticks after source activation before cascade check
}
```

**Example:**

```
CASCADE: NAT_DISASTER → INSURANCE_FAILURE
  variable: infrastructure_damage
  operator: '>'
  value: 0.7
  probability: 0.6
  magnitude_factor: 0.67   (insurance failure is 2/3 the disaster magnitude)
  delay_ticks: 10
```

### 5.4 Cascade Amplification Loops

Certain cascades create positive feedback loops that can lead to systemic collapse:

| Loop | Path | Description |
|------|------|-------------|
| **Insurance Death Spiral** | `INSURANCE_FAILURE → MASS_TORT → INSURANCE_FAILURE` | Uncompensated tort victims further destabilize insurance |
| **Fragmentation Loop** | `COMPACT_SECESSION → FOREIGN_INVASION → COMPACT_SECESSION` | Secession weakens defense, inviting invasion, causing more secession |
| **Trust Collapse** | `GUILD_SCANDAL → CLASS_ACTION → FINANCIAL_CRISIS → GUILD_SCANDAL` | Cascading institutional delegitimization |
| **Demographic Trap** | `PANDEMIC → FINANCIAL_CRISIS → POPULATION_SHOCK → PANDEMIC` | Crisis conditions make population vulnerable to next outbreak |

**Break condition:** Each amplification loop must have at least one exit condition (typically policy intervention or external aid) that terminates the loop.

### 5.5 Cascade Overload (Simultaneous Event Limit)

The simulation imposes a **Systemic Stress Load** metric:

```
systemic_stress_load = Σ(active_events[i].magnitude × duration_remaining[i])
```

| Stress Load | Effect |
|-------------|--------|
| `< 10` | Normal operations |
| `10–20` | Reduced recovery rates (all λ values halved) |
| `20–30` | Critical — cascading probability doubled; recovery rates at 25% |
| `> 30` | Systemic collapse — simulation enters "emergency" mode where state machine transitions are frozen and only emergency response events can fire |

---

## 6. Event Interaction Matrix

### 6.1 Paired Event Interaction Table

Shows how the simultaneous or overlapping presence of two events affects overall system dynamics.

| Event Pair | Interaction | Net Effect |
|-----------|-------------|------------|
| Natural Disaster + Pandemic | Healthcare overload; relief efforts blocked by quarantine | `×1.8` damage multiplier |
| Foreign Invasion + Compact Secession | Defensive fragmentation guarantees territorial loss | `×2.0` cohesion damage |
| Mass Tort + Insurance Failure | Uncompensated victims trigger class action | `×1.5` cascade probability |
| Tech Disruption + Financial Crisis | No capital for transition investment; stranded assets | `×1.6` unemployment multiplier |
| Guild Scandal + Class Action | Systemic delegitimization; regime stability threatened | `×2.5` trust damage |
| Pandemic + Population Shock | Demographic double-hit; dependency crisis | `×1.7` dependency ratio increase |
| Natural Disaster + Foreign Invasion | Disaster diplomacy or disaster opportunism | Ambiguous: `×0.6` cohesion (rally effect) or `×2.0` territory loss |
| Mass Tort + Guild Scandal | Guild liability cascade; multiple guilds implicated | `×2.0` guild insolvency risk |
| Financial Crisis + Insurance Failure | Systemic financial collapse; bailout costs explode | `×2.5` compact debt increase |
| Compact Secession + Financial Crisis | Capital flight; remaining members also destabilized | `×2.0` revenue loss |
| Technology Disruption + Mass Tort | AI liability claims (who is responsible for autonomous decisions) | Novel tort class emerges |
| Pandemic + Foreign Invasion | Bioweapon suspicion; international relations collapse | `×1.5` compact cohesion loss |

### 6.2 Synergistic Collapse Scenarios

These are named multi-event cascades that the simulation should specifically test:

| Scenario | Trigger Sequence | Expected Outcome |
|----------|-----------------|-----------------|
| **"The Perfect Storm"** | Financial Crisis → Insurance Failure → Mass Tort → Class Action | Systemic compact crisis; requires federal-level intervention |
| **"The Breaking Point"** | Natural Disaster → Pandemic → Population Shock → Secession | Compact may dissolve under compound stress |
| **"Tech Apocalypse"** | Technology Disruption → Financial Crisis → Guild Scandal → Class Action | Liability state model fundamentally challenged by automation |
| **"War and Fracture"** | Foreign Invasion → Secession → Financial Crisis → Pandemic | Existential threat to compact survival |
| **"Institutional Decay"** | Guild Scandal → Mass Tort → Class Action → Secession | Gradual dissolution driven by corruption |

### 6.3 Contagion Propagation

Some events generate cascading failure via **systemic contagion** — the spread of instability through interconnected subsystems:

```
contagion_flow(target, source) = w × event_magnitude × exposure_ratio
```

Where `w` is the contagion weight, `exposure_ratio` is how much the target depends on the source.

**Contagion Channels:**

| Channel | Description | Propagation Speed |
|---------|-------------|-------------------|
| **Financial** | Interlinked debt and insurance obligations | Fast (1–5 ticks) |
| **Trust** | Public confidence erosion across institutions | Medium (10–30 ticks) |
| **Political** | Secession sentiment spreads to other members | Slow (30–90 ticks) |
| **Demographic** | Population movements spread crisis | Medium (10–60 ticks) |
| **Legal** | Precedent-setting judgments expand liability | Slow (60–180 ticks) |

---

## 7. Simulation Integration

### 7.1 Event Scheduler

The simulation should maintain an `EventScheduler` that:

1. At each tick, evaluates all probabilistic and conditional triggers
2. Maintains a priority queue of timed events
3. Checks cascade conditions for all active events
4. Respects the Systemic Stress Load cap (§5.5)
5. Enforces cooldown periods (same event cannot re-fire within `cooldown_ticks`)

### 7.2 Event Resolution Order

When multiple events trigger simultaneously, resolution follows:

1. **Exogenous Physical** (Natural Disaster, Pandemic) — resolved first as "acts of nature"
2. **Exogenous Human** (Foreign Invasion, Technology Disruption) — resolved second
3. **Endogenous Systemic** (Financial Crisis, Insurance Failure) — resolved third
4. **Endogenous Human** (Mass Tort, Guild Scandal, Class Action) — resolved last

This ordering prevents external shocks from being preempted by internal responses, and allows cascades to propagate naturally from physical → systemic → human.

### 7.3 Configurability

All event parameters should be configurable via a YAML/JSON configuration file at simulation startup:

```
events:
  natural_disaster:
    enabled: true
    base_probability: 0.02
    magnitude_min: 1.0
    magnitude_max: 10.0
    duration_min: 1
    duration_max: 90
    cooldown_ticks: 120
    cascade_enabled: true
  ...
```

### 7.4 Logging and Analysis

Each event should produce structured log entries:

```
{
  "tick": 245,
  "event": "NAT_DISASTER",
  "magnitude": 7.2,
  "target": "region_3",
  "status": "PEAK",
  "effects": { ... },
  "cascade_triggered": ["INSURANCE_FAILURE"],
  "stress_load_contribution": 4.8
}
```

### 7.5 Stress Testing Protocol

The event system should support an automated **Stress Testing Protocol** that:

1. Runs N simulations with randomized event sequences
2. Records survival rate (compact intact at simulation horizon)
3. Identifies which event combinations are most lethal
4. Calculates the `system_collapse_probability` as a function of cumulative stress

---

## Appendix A: Summary Event Registry

| # | Event | Symbol | Origin | Trigger | Key Parameter | Recovery Pattern |
|---|-------|--------|--------|---------|---------------|------------------|
| 1 | Natural Disaster | `NAT_DISASTER` | External | Probabilistic + Timed | magnitude (1–10) | Exp / Lin / Mkt / Perm |
| 2 | Foreign Invasion | `FOREIGN_INVASION` | External | Conditional | aggressor_strength (0.3–2.0) | Cond / Exp / Perm |
| 3 | Mass Tort | `MASS_TORT` | Internal | Conditional | magnitude (1–10) | Lin / Mkt / Perm |
| 4 | Technology Disruption | `TECH_DISRUPTION` | External/Internal | Timed + Probabilistic | adoption_rate (0.1–0.9) | Mkt / Exp / Perm |
| 5 | Insurance Market Failure | `INSURANCE_FAILURE` | Internal | Conditional | magnitude (1–10) | Lin / Mkt / Exp / Perm |
| 6 | Guild Scandal | `GUILD_SCANDAL` | Internal | Probabilistic + Conditional | magnitude (1–10) | Exp / Mkt / Perm |
| 7 | Compact Secession | `COMPACT_SECESSION` | Internal | Conditional | magnitude (1–10) | Lin / Perm / Cond |
| 8 | Pandemic | `PANDEMIC` | External | Probabilistic | lethality (0.001–0.10) | Lin / Exp / Hys / Perm |
| 9 | Population Shock | `POPULATION_SHOCK` | External/Internal | Conditional + Timed | magnitude (1–10) | Perm / Lin / Mkt |
| 10 | Class Action | `CLASS_ACTION` | Internal | Conditional | magnitude (1–10) | Lin / Exp / Perm |
| 11 | Financial Crisis | `FINANCIAL_CRISIS` | External/Internal | Probabilistic + Timed | magnitude (1–10) | Exp / Mkt / Lin / Perm |

## Appendix B: Key Metrics Reference

| Metric | Affected By | Used In |
|--------|-------------|---------|
| `compact_cohesion` | Foreign Invasion, Secession, Class Action, Financial Crisis, Guild Scandal | Secession trigger, cascade conditions |
| `insurance_solvency` | Insurance Failure, Financial Crisis, Mass Tort, Natural Disaster | Insurance Failure trigger, cascade conditions |
| `public_trust` | All events (direction varies) | Recovery rate modifier, Class Action trigger |
| `inequality_index` | Tech Disruption, Financial Crisis, Pandemic, Population Shock | Class Action trigger, recovery modifier |
| `guild_safety_compliance` | Guild Scandal, Mass Tort | Mass Tort trigger |
| `systemic_leverage` | Financial Crisis | Financial Crisis trigger |
| `grievance_index` | Composite of inequality, trust, uninsured, uncompensated | Class Action trigger |

---

*End of Event & Stress Model Specification v1.0*
