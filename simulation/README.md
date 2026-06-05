# Liability State — Economic Simulation

## Purpose

Build a full economic simulation of the Liability State to answer questions that theory alone cannot:

1. **Will it actually work?** — Does the system function as a coherent economy, or do the mechanics conflict in ways that cause collapse?
2. **What are the actual economic flows?** — How much is LVT? How big is the Dividend? What are insurance premiums? How much goes to courts? Every dollar traced.
3. **What's it like to live in?** — What is the daily experience of a worker, a business owner, a guild member? Do they feel secure? Can they get ahead?
4. **What structures form?** — Do companies conglomeration? Do guilds become power blocs? Do court hierarchies centralize? Does wealth concentrate?
5. **What are the failure modes?** — Under what conditions does the system break? Does it recover on its own?
6. **What's missing?** — What assumptions in the theory are wrong? What mechanics are needed that nobody thought of?
7. **How resilient is it?** — External shocks (invasion, natural disaster, depression). Internal shocks (mass tort, insurance failure, guild collapse).

---

## The Money Flow (Everything Must Balance)

Every simulation step must track every dollar. The economic engine is a closed system:

```
                    ┌─────────────────────┐
                    │    CITIZENS earn     │
                    │  - Labor income      │
                    │  - Citizen's Dividend│
                    │  - Insurance payouts │
                    │  - Court awards      │
                    └──────────┬──────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
    ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
    │   LVT to       │  │  Premiums to  │  │  Court fees   │
    │  National Trust│  │   Insurers    │  │  to courts    │
    └───────┬───────┘  └───────┬───────┘  └───────┬───────┘
            │                  │                  │
            ▼                  ▼                  ▼
    ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
    │  → Dividend   │  │  → Pays claims│  │  → Pays       │
    │  → Alliance   │  │  → Profit/    │  │    judges,    │
    │    skim       │  │    loss       │  │    refunds    │
    └───────────────┘  └───────────────┘  └───────────────┘
```

**No money is created or destroyed.** Every inflow has a corresponding outflow. Every agent has a balance sheet. The simulation tracks:

| Flow | Where from | Where to | Recorded by |
|------|-----------|---------|-------------|
| Labor income | Employer | Worker | Wallet transfer |
| LVT payment | Landowner | National Trust | Land registry |
| Alliance skim | National Trust | Alliance budget | Constitution |
| Citizen's Dividend | National Trust | Every citizen | Universal payment |
| Insurance premium | Policyholder | Insurer pool | Insurance contract |
| Insurance claim | Insurer pool | Claimant | Claims process |
| Court filing fee | Plaintiff | Court | Case record |
| Court award | Defendant | Plaintiff | Judgment |
| Court costs | Court | Judge/administrator | Budget line |
| Harberger purchase | Buyer | Seller | Property transfer |
| Guild dues | Guild member | Guild mutual | Membership record |
| Surety bond | Bond poster | Escrow | Bond registry |
| Investment | Investor | Company | Partnership agreement |

---

## Agent Experience (What It's Like to Live Here)

Beyond money, each agent has a **wellbeing score** — a composite of:

| Factor | What it measures | How it's calculated |
|--------|-----------------|---------------------|
| **Wealth** | Assets minus debts | Cash + property value - mortgages - liabilities |
| **Security** | Risk of catastrophic loss | Insurance coverage level, liability exposure |
| **Freedom** | Ability to act without permission | Ex-ante licensing burden, court accessibility |
| **Community** | Social connection | Guild membership, compact identity, trust network |
| **Purpose** | Meaningful work and advancement | Career progression, skill development, entrepreneurial opportunity |

Each agent has a **life narrative** — not just statistics but a sequence of events:
- "Received Dividend: $850"
- "Filed insurance claim after car accident: $12,000"
- "Sued by neighbor for noise pollution: lost, owed $500"
- "Changed guild from machinists to electricians"
- "Bought land parcel via Harberger auction"
- "Premium increased 30% after filing two claims"

These narratives, aggregated across agent types, show what the system actually feels like to live in.

---

## Emergent Structure Detection

The simulation watches for structures that form spontaneously:

| Structure | How it emerges | What to watch for |
|-----------|---------------|-------------------|
| **Corporate hierarchies** | Companies grow, acquire, or splinter | Market concentration (Herfindahl index), subsidiary formation |
| **Guild power blocs** | Guilds accumulate influence | Membership concentration, Guild mutual sizes, certification monopolies |
| **Court reputation rankings** | Some courts attract more cases | Case volume distribution across courts, appeal rates |
| **Compact specialization** | Compacts differentiate | Migration flows, economic activity by compact |
| **Wealth stratification** | Classes form | Gini over time, mobility between quintiles |
| **Insurance market concentration** | Insurers merge or fail | Number of insurers, premium share distribution |
| **Land ownership patterns** | Land accumulates | Fraction of land owned by top 10% of agents |

---

## Failure Mode Detection

The simulation actively flags:

| Failure mode | Indicator | What triggers it |
|-------------|-----------|-----------------|
| **Insurance death spiral** | Premiums rise faster than claims | Adverse selection or correlated risk overwhelms pool |
| **Court gridlock** | Backlog exceeds capacity | Filing fee too low, too many frivolous suits |
| **Dividend trap** | People choose Dividend over work | Dividend exceeds median labor income |
| **Harberger collapse** | Land values plummet | Mass under-declaration or coordinated gaming |
| **Alliance capture** | Alliance budget grows without compact approval | Spend rate exceeds 90% of skim |
| **Capital flight** | Investment dries up | No safe assets, court uncertainty, liability fear |
| **Guild monopoly** | One guild controls a critical sector | Certification bottlenecks, wage suppression |
| **Conquest incentive** | Compacts profit from invading | LVT contribution of invaded territory exceeds invasion cost |
| **Wealth cascade** | Richest agents accumulate all gains | Gini rises past 0.8 without reversing |
| **Liquidity crisis** | No one can pay judgments | Court awards exceed defendant assets systematically |

---

## Event Injection (Stress Testing)

The simulation can inject external and internal events mid-run:

| Event | Type | What it tests |
|-------|------|---------------|
| **Natural disaster** | External | Insurance market capacity, rebuilding, dividend as shock absorber |
| **Foreign invasion** | External | War bond mechanism, PMC mobilization, post-war incorporation |
| **Mass tort** | Internal | Court system capacity, insurer solvency, bankruptcy cascade |
| **Technology disruption** | External | Industry collapse, guild adaptation, Harberger IP revaluation |
| **Insurance market failure** | Internal | Systemic risk, Alliance backstop, recovery |
| **Guild scandal** | Internal | Certification collapse, trust erosion, alternative guild formation |
| **Compact secession** | Internal | STO enforcement, trade disruption, currency split risk |
| **Pandemic** | External | Healthcare insurance, dividend as UBI, business interruption |
| **Population boom/crash** | External | LVT base expansion/contraction, Dividend adjustment |

---

## Build Plan

### Phase 0: Economic Engine (Money Flow Core)

Build the accounting layer that tracks every dollar. No agents yet — just the mechanics running against parameterized inputs to verify money balances.

| Step | Deliverable | What it proves |
|------|-------------|----------------|
| 0.1 | Money tracking system | Every agent has a ledger. Every transfer is recorded. Zero-balance invariant checked each step. |
| 0.2 | LVT + National Trust + Dividend loop | LVT collected from landowners → Trust → skim to Alliance + Dividend to citizens. Money balances to zero. |
| 0.3 | Insurance pool | Premiums collected → claims paid + insurer profit/loss. Pool solvency tracked. |
| 0.4 | Court system | Filing fees → case adjudication → awards enforced. Budget balances. |
| 0.5 | Harberger property market | Self-assessment → forced sale → LVT adjustment. Land registry tracks ownership. |

### Phase 1: Lightweight Validation

Run the validated mechanics against known phenomena to confirm they produce expected behaviors.

| Step | What it tests | Expected behavior |
|------|---------------|-------------------|
| 1.1 | Insurance with info asymmetry | Adverse selection when insurer can't distinguish risk types |
| 1.2 | LVT vs income tax | LVT doesn't distort labor, income tax does |
| 1.3 | Tort liability vs care level | Higher liability → more care → fewer accidents |
| 1.4 | Harberger self-assessment | Declared values converge toward market price under forced-sale threat |

### Phase 2: Full Agent Society

Populate the economic engine with self-interested agents.

| Step | Deliverable | What agents can do |
|------|-------------|-------------------|
| 2.1 | Worker agents | Choose labor (hours, occupation), buy insurance, rent/buy land, save/spend, migrate between compacts |
| 2.2 | Business agents | Hire workers, set prices, buy insurance, invest, form partnerships, spin off subsidiaries |
| 2.3 | Insurer agents | Set premiums, evaluate risk, collect pools, pay claims, invest reserves, compete for customers |
| 2.4 | Guild agents | Set certification standards, collect dues, manage mutual pool, lobby compacts |
| 2.5 | Court agents | Set fees, adjudicate cases, set precedents, compete for reputation |

### Phase 3: Adversarial Behavior Layer

Agents can switch between honest and exploitative strategies based on expected value.

| Strategy | What agent does | Condition to trigger |
|----------|----------------|---------------------|
| **Premium evasion** | Under-report risk to insurer | Expected savings > probability of detection × penalty |
| **Court flooding** | File frivolous suits hoping for settlement | Expected settlement > filing fee |
| **Harberger gaming** | Under-declare land value, collude with buyer | Side payment + expected tax savings > LVT on true value |
| **Insurance fraud** | Fake a claim | Expected payout > probability of detection × penalty + premium increase |
| **Guild rent-seeking** | Restrict membership to raise wages | Reduced competition → higher member income > lost dues from excluded workers |
| **Forum shopping** | File cases in court with most favorable bias | Expected award difference > transfer costs |
| **Collusion** | Coordinate prices with competitors | Expected profit increase > probability of detection × antitrust penalty |
| **Tax sheltering** | Shift income/land to lower-LVT compact | Tax savings > migration costs |

### Phase 4: Long-Run Observation Runs

| Run | Duration | Question |
|-----|----------|---------|
| **Baseline** | 500 steps | Does the system reach a stable equilibrium? What does it look like? |
| **High adversity** | 500 steps | When many agents exploit, does the system correct or collapse? |
| **Shock test** | 300+ steps | Inject a disaster at step 100. Does the system recover? How long? |
| **Parameter sweep** | 200 steps × 50 configs | Vary LVT rate, liability cap, court fees. Find tipping points. |
| **Compact competition** | 400 steps | Multiple compacts with different rules. Do agents sort themselves optimally? |
| **Very long run** | 2,000 steps | What does the system look like after generations? Does wealth concentrate? |

---

## Key Questions the Simulation Should Answer

### Viability
- Does the LVT collect enough revenue to fund the Dividend and Alliance functions?
- Do insurance companies remain solvent under realistic claim rates?
- Does the court system keep up with caseloads?
- Can agents actually get insured at reasonable rates?

### Lived Experience
- What is the median agent's wealth trajectory over 20 years?
- How common are catastrophic losses (uninsured or under-compensated)?
- Can a poor agent realistically become wealthy?
- What fraction of income goes to insurance premiums vs. LVT vs. other costs?
- How often does the average agent interact with the court system?

### Failure Modes
- Under what conditions does the insurance market fail?
- Does litigiousness break the court system?
- Can a concentrated group of agents game the Harberger system?
- What happens to land values in a recession? Does the LVT crash?
- Does the Dividend floor work as intended, or does it trap people?

### Missing Mechanics
- Are there behaviors agents attempt that the current rules don't cover?
- Do agents find ways to externalize harm that the liability system doesn't catch?
- Are there obvious arbitrage opportunities the system should prevent?
- Do agents create institutions (new guilds, new court types, new financial instruments) that the theory didn't design?

---

## Output Format

For each run, the simulation produces:

1. **Balance sheet** — Every agent's assets, liabilities, income, and expenses per step
2. **Flow matrix** — Total dollars moved between every pair of system components per step
3. **Agent narratives** — Key life events for a sample of agents across all types
4. **Structure timeline** — When structures formed, grew, and collapsed
5. **Failure flags** — When any failure indicator triggered and what happened
6. **Parameter log** — The exact configuration used, for reproducibility
7. **Maps/heatmaps** — Land values, premium rates, court densities across compacts (visual)

---

## Directory Structure

```
simulation/
├── README.md
├── config/
│   ├── default.yaml
│   ├── validation/          # V1-V4 validation configs
│   └── scenarios/           # Long-run scenario configs
├── src/
│   ├── core/                # Money tracking, ledger, scheduler
│   │   ├── ledger.py        # Every agent's balance sheet
│   │   ├── flow_tracker.py  # Inter-component money flows
│   │   └── scheduler.py     # Step execution order
│   ├── mechanics/           # LS rule implementations
│   │   ├── lvt.py
│   │   ├── insurance.py
│   │   ├── courts.py
│   │   ├── dividend.py
│   │   ├── harberger.py
│   │   ├── guilds.py
│   │   ├── alliance.py      # Skim, refund, sunset
│   │   └── war.py           # War bond, conquest costs
│   ├── agents/              # Agent types
│   │   ├── base_agent.py
│   │   ├── worker.py
│   │   ├── business.py
│   │   ├── insurer.py
│   │   └── guild.py
│   ├── adversarial/         # Exploit strategy library
│   │   ├── strategies.py
│   │   └── controller.py    # Decides when agent switches to exploit
│   ├── events/              # Shock injection
│   │   ├── disaster.py
│   │   ├── invasion.py
│   │   └── market_fail.py
│   ├── analysis/            # Output processing
│   │   ├── satisfaction.py  # Wellbeing scoring
│   │   ├── structures.py    # Hierarchy/pattern detection
│   │   ├── failures.py      # Failure mode checking
│   │   └── narrative.py     # Life event generation
│   └── environment.py       # Main simulation
├── validation/
│   ├── v1_adverse_selection.py
│   ├── v2_lvt_efficiency.py
│   ├── v3_tort_deterrence.py
│   └── v4_harberger.py
├── experiments/
│   ├── run_baseline.py
│   ├── run_validation.py
│   └── parameter_sweep.py
└── output/
    ├── logs/
    ├── flows/
    ├── narratives/
    └── figures/
```

---

## Technology Choices

| Component | Choice | Why |
|-----------|--------|-----|
| **Framework** | Custom Python (not Mesa) | Mesa is designed for abstract ABMs with simple agents. We need a full double-entry accounting engine. Starting from scratch gives us control over the money tracking invariant. |
| **Language** | Python 3.11+ | Fast prototyping, NumPy for array operations on batches of agents |
| **Data** | SQLite for per-run storage | Every step, every balance, every flow — relational queries across runs |
| **Numerics** | NumPy + Pandas | Bulk agent operations, time series analysis |
| **Visualization** | Matplotlib + networkx | Flow diagrams, structure graphs, time series, heatmaps |
| **Config** | YAML | Human-readable, nested, version-controllable |
