# Liability State Economic Simulator — Complete Mechanism Reference

Every config key in `comparison_phase8.py` documented with purpose,
default, range, and rationale. 57 mechanisms total.

---

## How to Use This Reference

Each mechanism entry follows the same format:

```
**key** = default | range       — one-line summary
  What it does: ...
  Why it exists: ...
  Data: ...
```

Mechanisms are grouped by category. All default to OFF/0 unless noted.

---

## 1. TAX SYSTEM (10 keys)

### 1.1 `tax_type` = `'lvt'` | `'lvt'`, `'income'`, `'none'`
  **What it does:** Selects the tax regime for the simulation.
  - `'lvt'`: Land Value Tax. Tax is levied on land holdings at `lvt_rate`.
    Revenue flows to 'trust' (National Trust), not 'sys'. Dividend
    mechanism distributes trust revenue back to citizens equally.
  - `'income'`: Income Tax. Wages taxed at `income_tax_rate`, corporate
    profits at `corp_tax_rate`. Revenue flows to 'sys' for welfare,
    courts, CPF, and government spending.
  - `'none'`: No tax. Used for laissez-faire systems.
  **Why it exists:** The core institutional comparison of the simulator.
  LVT vs income tax is the central policy question of the Liability State
  framework. LVT is Georgist: tax land, not labor. Income tax is the
  conventional modern system.
  **Heritage:** Phase 4 (comparison_phase4.py).

### 1.2 `lvt_rate` = Phase 4 default | [0, ~0.1]
  **What it does:** Annual Land Value Tax rate. Applied monthly as
  `lvt_rate / 12` on each agent's land holdings. Only active when
  `tax_type='lvt'`. Revenue funds the citizen dividend.
  **Why it exists:** Core Georgist mechanism. Henry George argued land
  value tax is efficient because land supply is fixed (no deadweight loss
  from taxation).
  **Heritage:** Phase 4.

### 1.3 `income_tax_rate` = `0.0` | [0, 0.7]
  **What it does:** Flat rate on wage income. Only active when
  `tax_type='income'`. When `use_progressive_tax=True`, this key is
  ignored in favor of progressive brackets. Informal workers are exempt.
  **Why it exists:** Baseline income tax. Represents the effective average
  tax rate on labor income.
  **Data:** OECD Tax Database.

### 1.4 `use_progressive_tax` = `False` | bool
  **What it does:** When True and `tax_type='income'`, replaces the flat
  `income_tax_rate` with progressive brackets scaled to the simulation's
  median annual income. Brackets are proportional to US 2020 IRS rates:
  - 10% on income 0–0.44× median
  - 15% on 0.44–1.11× median
  - 25% on 1.11–2.22× median
  - 35% on 2.22–4.44× median
  - 40% on income over 4.44× median
  At simulation wages ($25/hr, $300/mo), median annual = $3,600:
  $0–$1,600 → 10%, $1,600–$4,000 → 15%, $4,000–$8,000 → 25%,
  $8,000–$16,000 → 35%, $16,000+ → 40%.
  **Why it exists:** Progressive tax is the primary fiscal inequality
  reducer. The original implementation used fixed US-dollar brackets
  ($20k–$200k+) that were unreachable at simulation incomes (~$2,400–
  $9,600 total). Fixed via median-ratio scaling so brackets always
  capture the relevant range.
  **Data:** IRS Revenue Procedure 2019-44; brackets expressed as ratios
  of median household income ($45,000). Default False for backward
  compatibility.

### 1.5 `top_marginal_surcharge` = `0.0` | [0, 1]
  **What it does:** Additional tax rate applied to top earners, sorted
  by wealth percentile. `top_surcharge_threshold` (default 0.8 = top
  20% of workers) determines which workers pay it. The surcharge is
  additive to the base income tax. At 0.15 (15% surcharge) on the top
  20%: a top-quartile worker earning $5,000/mo in a 20% base bracket
  pays $1,000 base + $750 surcharge = $1,750 total.
  **Effect:** Empirically, a 15% surcharge on the top 20% reduces Gini
  by -0.019 (US_Style config, all other mechanisms OFF).
  **Why it exists:** Replaces `wage_ratio_cap` which was flagged as
  arbitrary (no country has enacted binding CEO-to-worker pay caps).
  Top marginal surcharges are real policies: US ACA 0.9% Medicare
  surtax on high earners, UK 45% additional rate above £150k, France
  75% millionaire tax (2013-2014), US historic top rates of 70-91%
  (1930s-1970s). This is a tax mechanism, not a wage control, and
  operates through the tax system rather than direct wage capping.
  **Data:** Piketty, T. & Saez, E. (2003) \"Income inequality in the
  United States.\" QJE 118(1). IRS statistics of income.
  **Scope:** General top-end progressive taxation. For cooperative
  internal wage ratios, see `wage_ratio_cap` (coop-only).

### 1.6 `corp_tax_rate` = `0.0` | [0, 0.55]
  **What it does:** Tax on corporate profits. Applied to business profit
  after revenue minus BUSINESS_WAGE_BILL. Only active when
  `tax_type='income'`. Revenue flows to 'sys'.
  **Why it exists:** Corporate income tax is a major revenue source.
  US statutory rate fell from 52% (1960s) to 21% (2020s), OECD average ~23%.
  **Data:** OECD Corporate Tax Statistics.

### 1.7 `vat_rate` = `0.20` | [0, 0.3]
  **What it does:** Value-Added Tax rate on wages. Only active when
  `use_vat=True`. Represents consumption tax systems common in Europe.
  **Why it exists:** VAT is the third major tax regime modeled. It's
  regressive (taxes consumption, which takes a larger share of poor
  incomes) but efficient (broad base, hard to evade).
  **Heritage:** Phase 4.

### 1.8 `use_vat` = `False` | bool
  **What it does:** Enables VAT as the tax type (overrides income/lvt).
  Combined with `vat_rate`.
  **Why it exists:** Used for the UBI+VAT system comparison model.

### 1.9 `welfare_rate` = `0.0` | [0, 0.3]
  **What it does:** Fraction of tax revenue (`tt`) redistributed as a
  universal flat payment to formal-sector workers each step. Informal
  workers are excluded. At 0.20: 20% of tax revenue goes to welfare.
  **Why it exists:** Welfare transfers are the main channel through which
  tax revenue reduces inequality. Countries vary from ~0.03 (US 1960s)
  to ~0.20 (France 2020s).
  **Data:** OECD Social Expenditure Database.

### 1.10 `admin_overhead` = from Phase 4 | [0, 0.1]
  **What it does:** Fraction of tax revenue consumed by administrative
  overhead (waste). Varies by tax type: LVT has lower overhead than
  income tax (no filing, no avoidance).
  **Why it exists:** Models the efficiency difference between tax systems.
  LVT has near-zero collection cost because land can't be hidden. Income
  tax requires auditing, withholding, and enforcement.
  **Heritage:** Phase 4.

---

## 2. LABOR MARKET (9 keys)

### 2.1 `skill_premium_growth` = `0.0` | [0, 0.05]
  **What it does:** Annual compounding wage premium for the top 50% of
  workers by hourly wage. Applied every 12 steps. At 0.015 (1.5%/yr):
  `1.015^20 = 1.35`, creating a 35% wage gap between top and bottom
  halves over 20 years.
  **Why it exists:** Skill-biased technical change (SBTC) is the dominant
  explanation for rising wage inequality since 1980 (Autor, Katz & Krueger
  1998; Acemoglu 2002). Computerization complements high-skill workers,
  substitutes for routine tasks.
  **Data:** Autor, D. (2014) "Skills, education, and the rise of earnings
  inequality." Science 344.

### 2.2 `union_coverage` = `0.0` | [0, 1]
  **What it does:** Compresses the wage distribution. Workers below the
  median wage receive a boost (10% × coverage). Workers above the median
  face a competitive penalty (5% × coverage). At 0.35 (US 1960s): bottom
  50% get +3.5%, top 50% lose -1.75%.
  **Why it exists:** Unions raise wages at the bottom and constrain them
  at the top (Freeman & Medoff 1984; Card, Lemieux & Riddell 2004).
  Union coverage declined from ~35% (US 1960s) to ~10% (2020s).
  **Data:** OECD/AIAS ICTWSS database.

### 2.3 `union_premium` = `1.0` | [0.8, 1.3]
  **What it does:** Multiplicative premium on wages for all union-covered
  workers. At 1.15: union workers earn 15% more than their baseline wage.
  **Why it exists:** The union wage premium is distinct from coverage
  compression. Unions bargain for higher wages for their members, creating
  a premium. Premium declined as unions weakened.
  **Heritage:** Phase 4.

### 2.4 `capital_income_share` = `0.0` | [0, 0.3]
  **What it does:** Financialization mechanism. After businesses pay taxes,
  a fraction of after-tax profit (this key) is diverted from 'sys' to
  the top 10% wealthiest workers, proportional to their wealth. At 0.15:
  15% of business profits flow to the top decile.
  **Why it exists:** Financialization — the growing share of economic
  activity accruing to finance — has driven inequality since 1980 (Piketty
  2014, Krippner 2011). The top 10% own ~85% of financial assets.
  **Data:** Piketty, T. (2014) "Capital in the 21st Century."

### 2.5 `import_competition` = `0.0` | [0, 0.5]
  **What it does:** Suppresses wages for the bottom 25% of workers by
  hourly wage. Each unit of competition reduces their wages by 2%.
  At 0.20 (US 2020s): bottom quartile loses 4%.
  **Why it exists:** Import competition from China and other low-wage
  countries disproportionately hurts low-skill manufacturing workers
  (Autor, Dorn & Hanson 2013). The "China shock" is well-documented.
  **Data:** Autor, Dorn & Hanson (2013) "The China Syndrome." AER 103.

### 2.6 `minimum_wage` = `0.0` | [0, ~50]
  **What it does:** Floor on hourly wages. If a worker's calculated wage
  falls below this value, it's raised to the minimum. Set to $7.25/hr
  for US federal minimum wage.
  **Why it exists:** Minimum wage laws exist in most countries. They
  compress the bottom of the wage distribution but may reduce employment
  (Neumark & Wascher 2008).
  **Heritage:** Phase 4.

### 2.7 `wage_ratio_cap` = `5` | int ≥ 1 (coop-specific)
  **What it does:** Caps the ratio of highest to lowest wage distribution
  within worker cooperatives. Only active when `use_worker_coop=True`.
  At 5:1, the maximum cooperative distribution to a single worker is
  capped at 5× the minimum monthly wage, preventing extreme pay
  dispersion inside coops.
  **Why it exists:** Worker cooperatives typically enforce internal wage
  ratios as a governance rule (Ellerman 1992). Mondragon uses 6:1.
  **Scope:** This is a **cooperative governance parameter**, not a
  general economy-wide policy. For general top-end taxation, use
  `top_marginal_surcharge`. Wage_ratio_cap was previously flagged as
  arbitrary when interpreted as a general CEO pay cap — the coop-only
  context resolves this concern.
  **Data:** Mondragon Corporation wage ratio policy; Ellerman, D. (1992)
  "Property & Contract in Economics."

### 2.8 `labor_supply_elasticity` = `0.2` | [0, 1]
  **What it does:** The Frisch elasticity of labor supply. Determines how
  much workers reduce hours when taxes increase. At 0.2: a 10% tax
  increase reduces labor supply by 2%.
  **Why it exists:** The elasticity determines the efficiency cost of
  taxation. LVT advocates argue land taxes have zero distortion because
  land supply is fixed. Income taxes distort labor supply.
  **Data:** Chetty, R. (2012) "Bounds on elasticities with optimization
  frictions." Econometrica 80(3).

### 2.9 `tax_efficiency_loss` = `0.0` | [0, 1]
  **What it does:** Harberger deadweight loss parameter η. When > 0,
  taxes impose an efficiency cost on business output (not just labor
  supply). DWL = 0.5 × η × t² × revenue, where t = effective tax rate.
  At η = 0.4 (central estimate), a 30% income tax reduces business
  revenue by 0.5 × 0.4 × 0.09 = 1.8% from the efficient baseline.
  **Why it exists:** The efficiency cost of taxation is well-estimated
  from compensated labor supply elasticities (Chetty 2012) and tax
  responsiveness (Gruber & Saez 2002). η ≈ 0.3–0.5 for labor income
  tax. LVT has near-zero DWL (land is fixed supply).
  **Replaces:** `TFP_TAX_ELASTICITY` which suffered from severe
  endogeneity: taxes and TFP are jointly determined by common factors
  (institutions, rule of law, human capital). The original parameter
  had no clean empirical identification. `tax_efficiency_loss` uses
  well-estimated compensated elasticities from quasi-experimental data.
  **Data:** Chetty, R. (2012) \"Bounds on elasticities with optimization
  frictions.\" Econometrica 80(3); Gruber & Saez (2002) AER 92(4).
  **Legacy fallback:** `TFP_TAX_ELASTICITY` is still supported but
  defaults to 0 (OFF). Set it explicitly in config if needed.

---

## 3. INFORMAL & DUAL LABOR MARKETS (2 keys)

### 3.1 `informal_share` = `0.0` | [0, 1]
  **What it does:** The bottom fraction of workers by hourly wage are
  marked as "informal." They receive a wage penalty, pay no income tax,
  and are excluded from welfare benefits. At 0.85 (India): 85% of workers
  are informal.
  **How it works:**
  1. Each step, workers are sorted by hourly wage. The bottom
     `informal_share` are flagged.
  2. Their wage income is multiplied by `informal_wage_penalty`.
  3. In the tax section, flagged workers are skipped (no income tax).
  4. In the welfare section, flagged workers are excluded from benefit
     distribution.
  **Why it exists:** The informal sector dominates developing economies
  (ILO 2018). Informal workers earn 40-60% less, pay no tax, receive no
  welfare. This simultaneously reduces government revenue and increases
  inequality. The mechanism shows diminishing returns above ~70%: once
  most workers are informal, formal-sector changes barely affect total
  inequality. This explains why India's Gini (~0.48) is stable despite
  massive formal-sector growth.
  **Data:** ILO (2023) "Women and Men in the Informal Economy," 3rd ed.
  **Countries:** India (0.80-0.85), Brazil (0.38-0.45), China (0.05-0.40),
  Japan (0.10-0.35 non-regular workers), South Korea (~0.22).
  **Saturates above ~70%.**

### 3.2 `informal_wage_penalty` = `0.5` | [0.1, 1.0]
  **What it does:** Multiplier on informal sector wages. At 0.5: informal
  workers earn 50% of their baseline wage. At 1.0: no penalty (informal
  workers earn the same as formal — useful for modeling welfare-access
  exclusion without wage discrimination).
  **Why it exists:** The informal wage penalty varies by country and is
  independently estimated from household surveys. India's penalty is
  ~0.4 (Chen & Raveendran 2014), Brazil's ~0.5 (Botelho & Ponczek 2011).
  **Data:** Chen, M. & Raveendran, G. (2014) "Urban employment in India."
  WIEGO Statistical Brief.

---

## 4. WAGE DETERMINATION & SKILLS (2 keys)

### 4.1 `education_variance` = `0.0` | [0, 1]
  **What it does:** Stretches the top of the wage distribution
  proportionally to education system inequality. Applied once at
  initialization (not per-step). Uses an asymmetric log-normal stretch:
  workers above the median wage get their deviation from median multiplied
  by `1 + edu_var × 2.0`. Workers below the median are unchanged (minimum
  wage floor effect). The median wage ($25/hr) is preserved.
  **90/10 ratios produced:**
  | ev | Example country | 90/10 ratio |
  |:--:|:---------------:|:-----------:|
  | 0 | Baseline (uniform) | 2.85x |
  | 0.30 | Finland | ~2.5x |
  | 0.40 | Japan | ~3.0x |
  | 0.55 | Germany | ~3.5x |
  | 0.60 | France | ~4.0x |
  | 0.70 | US | ~5.0x |
  **Post-tax Ginis:** France ev=0.60 produces post-tax Gini 0.305
  (actual 0.30, within 2%). US ev=0.70 produces post-tax Gini 0.343
  with all mechanisms (actual 0.48, 59% gap closed).
  **Why it exists:** Education system inequality is a causal driver of
  wage inequality (Hanushek & Woessmann 2008). Countries with more unequal
  schools produce workers with more unequal skills → more unequal wages.
  OECD PISA data shows between-school variance explains 60-70% of
  cross-country 90/10 variation. The asymmetric stretch (top pulls away,
  bottom doesn't fall) reflects how unequal education primarily affects
  the top through elite university access and skill premiums.
  **Data:** OECD PISA 2022, Table II.2.6 (between-school variance).
  Default=0 for backward compatibility with the uniform baseline.

### 4.2 `wage_dispersion_mult` = `1.0` | [1, 10] (legacy fallback)
  **What it does:** Legacy mechanism. If `education_variance=0` and this
  key exceeds 1.0, applies a linear stretch to the wage distribution
  (median + deviation × mult, clipped at 40% of median).
  **Note:** Replaced by `education_variance` which is causal. This key
  is preserved for backward compatibility with existing configs.

---

## 5. ASSET & WEALTH CONCENTRATION (4 keys)

### 5.1 `capital_income_concentration` = `0.0` | [0, 1]
  **What it does:** After businesses generate after-tax profit, a fraction
  (`capital_income_concentration` × total_profit) is distributed to the
  top `capital_income_top_share` of workers by wealth, proportionally to
  their wealth. At 0.3, top 10%: 30% of business profits flow to the
  wealthiest decile, increasing Gini by ~+0.033 (US_Style).
  **Requires:** Business profit to exist. The business profit bug
  (L=8→L=750 fix) was necessary for this to function. See Section 14.
  **Why it exists:** Capital ownership is the most concentrated asset.
  The top 10% own ~85% of corporate equity (Saez & Zucman 2016). When
  businesses profit, wealthy shareholders capture almost all gains.
  This is the Piketty r > g channel. The model previously had NO capital
  income channel — this was its single largest omission.
  **Data:** Saez, E. & Zucman, G. (2016) "Wealth inequality in the US
  since 1913." QJE 131(2). WID.world.

### 5.2 `capital_income_top_share` = `0.1` | [0.01, 1]
  **What it does:** The fraction of workers who receive capital income.
  At 0.1: top 10% receive it. At 0.01: top 1% only (more concentrated).
  **Why it exists:** Different countries concentrate capital ownership
  differently. The US top 1% own ~40% of wealth; Nordic top 1% own ~20%.

### 5.3 `housing_wealth_concentration` = `0.0` | [0, 0.5]
  **What it does:** Annual property market effect. Annually (step % 12):
  1. Top 10% by wealth receive housing gains: `wealth × housing_wealth × 0.03`
  2. Bottom 75% lose housing affordability: `wealth × housing_wealth × 0.005`
  At 0.40 (UK 2020s): top decile gains 1.2% of wealth/year from housing;
  bottom 75% loses 0.2%.
  **Why it exists:** Housing wealth is the largest component of
  middle-class wealth and the primary inequality driver in the UK
  (Atkinson 2015). UK house prices rose 4× relative to income (1980-2020).
  **Data:** UK Land Registry price index. Bank of England (2020).

### 5.4 `patrimonial_wealth` = `0.0` | [0, 1]
  **What it does:** Annual rent transfer from 'sys' to the top 5%
  wealthiest workers. Pool = `total_worker_wealth × patrimonial × 0.01`.
  40% of this pool goes to the top 5% proportionally. At 0.8 (Brazil
  1960s): 0.8% of total worker wealth flows to the top 5% each year,
  producing Gini ~0.51-0.62.
  **Why it exists:** Brazil has the world's highest land Gini (0.87).
  A small oligarchy controls vast landholdings, mines, and infrastructure
  (Souza 2018). This is distinct from SBTC — it's about owning resources,
  not skills. Bolsa Família and land reform reduced this over time,
  which the model captures via declining parameter values.
  **Data:** Souza, P. (2018) "A History of Inequality: Top Incomes in
  Brazil." WID.world. Oxfam (2016) "An Economy for the 1%."

---

## 6. INCOME EFFECTS & REDISTRIBUTION (3 keys)

### 6.1 `income_effect_labor` = `0.0` | [0, 0.15]
  **What it does:** When workers receive non-labor income (dividends,
  welfare), they may reduce labor supply. At 0.10: the income effect
  reduces hours by up to 10% for workers receiving significant transfers.
  **Why it exists:** The income effect of transfers on labor supply is
  a key concern in welfare economics. LVT dividends may reduce work
  effort (though evidence is mixed).
  **Heritage:** Phase 6.

### 6.2 `elite_capture_intensity` = `0.0` | [0, 0.5]
  **What it does:** The top 10% wealthiest workers get tax avoidance.
  Their effective tax rate is multiplied by `max(0.7, 1 - percentile×capture)`.
  At 0.15 (US 2020s): the wealthiest 1% pay ~15% less tax than their
  statutory rate.
  **Why it exists:** Elite tax avoidance is a well-documented channel
  through which the rich reduce their effective tax rate (Saez & Zucman
  2019). Offshore accounts, carried interest, and tax shelters reduce
  progressivity.
  **Data:** Saez, E. & Zucman, G. (2019) "The Triumph of Injustice."

### 6.3 `cpf_rate` = `0.0` | [0, 0.4]
  **What it does:** Central Provident Fund (forced savings) rate. A
  fraction of total wages is deducted and redistributed equally to all
  agents as a forced savings pool. Models Singapore's CPF system.
  **Why it exists:** Singapore's CPF is a unique system combining forced
  savings, housing finance, and pension provision. It reduces inequality
  by giving workers a forced asset pool.
  **Heritage:** Phase 6.

---

## 7. COUNTRY-INSTITUTIONAL (6 keys)

### 7.1 `financial_services_premium` = `0.0` | [0, 0.3]
  **What it does:** The top 10% of workers by wage receive a premium
  (15% × premium). The bottom 50% face a wage suppression effect
  (3% × premium). Only meaningful for the UK.
  **Why it exists:** The UK has an oversized financial services sector
  (~10% of GDP vs ~5% comparable economies). This concentrates high
  wages in London while crowding out other industries (Bell & Van Reenen
  2014).
  **Data:** Bell, B. & Van Reenen, J. (2014) "Bankers and their bonuses."

### 7.2 `reunification_shock` = `0.0` | [0, 1]
  **What it does:** One-time event at simulation midpoint (step 120,
  ~1990). Workers lose 5% × reunification of their wealth (reunification
  tax). System pays solidarity surcharge (3% × reunification of sys
  balance) equally to all workers.
  **Why it exists:** German reunification (1990) was a massive wealth
  transfer from West to East through the Solidarity Surcharge.
  **Data:** Burda & Hunt (2001) "From reunification to economic
  integration." BPEA.

### 7.3 `hartz_reform` = `0.0` | [0, 1]
  **What it does:** The bottom 33% of workers face wage suppression
  (tiered from -10% to -5%) from labor liberalization. The top 33%
  receive a small benefit (+2%).
  **Why it exists:** The Hartz reforms (2003-2005) liberalized Germany's
  labor market, creating a "mini-jobs" sector that suppressed low-skill
  wages while benefiting high-skill workers through increased flexibility.
  **Data:** Dustmann et al. (2014) "From sick man of Europe." JEP 28(1).

### 7.4 `child_benefit_taper` = `0.0` | [0, 1]
  **What it does:** A fraction of tax revenue (`tt × taper × 0.5`) is
  distributed to the bottom 50% of workers by wealth. The poorest
  receive the most (taper_factor=1.0), phasing to 0.2 at the 50th
  percentile.
  **Why it exists:** France has one of the most generous child benefit
  systems. The Quotient Familial means-tests benefits progressively.
  **Data:** Piketty (2005) "Les hauts revenus en France."

### 7.5 `education_gdp_share` = `0.0` | [0, 0.1]
  **What it does:** Government education spending as GDP share. Funds
  human capital growth: each unit of GDP share produces 8% annual return
  (standard Mincerian return to schooling).
  **Why it exists:** Education spending raises worker productivity over
  time, affecting wage growth and potentially reducing inequality.
  **Heritage:** Phase 8b.

### 7.6 `healthcare_gdp_share` = `0.0` | [0, 0.2]
  **What it does:** Government healthcare spending as GDP share. Workers
  pay a healthcare premium proportional to their wages. Funds improve
  worker health, raising effective productivity by 50% of spending share.
  **Why it exists:** Healthcare systems vary enormously across countries
  (US 18% of GDP, Singapore 4%). Universal systems reduce inequality
  by delocalizing health access from income.
  **Heritage:** Phase 8b.

---

## 8. INHERITANCE & INTERGENERATIONAL (2 keys)

### 8.1 `inheritance_rate` = `0.0` | [0, 1]
  **What it does:** Fraction of total worker wealth redistributed at the
  end of the simulation. How it's distributed depends on `inherit_bequest`.
  **Why it exists:** Inheritance is a major channel of wealth
  concentration. The rate represents the fraction of wealth that flows
  through inheritance each generation (~30% in developed economies).

### 8.2 `inherit_bequest` = `False` | bool
  **What it does:** When False (default): inheritance is redistributed
  equally to all workers — a progressive transfer (takes from rich,
  gives to all). When True: inheritance flows proportionally to existing
  wealth — the wealthy receive more inheritance, compounding inequality.
  **Effect:** At `inheritance_rate=0.3`:
  - `inherit_bequest=False`: Gini compresses 0.145→0.135 (net transfer
    rich→poor)
  - `inherit_bequest=True`: Gini widens 0.145→0.195 (net transfer
    rich→rich)
  **Why the default (False) was wrong:** The original code took from
  each worker proportionally and gave equally to all. This is a death
  TAX, not inheritance. Real inheritance flows wealthy→wealthy. The
  parameter `inherit_bequest=True` corrects this.
  **Data:** Wolff, E. (2014) "Inheritance and wealth inequality."

---

## 9. MONETARY & BANKING (3 keys)

### 9.1 `money_creation_rate` = `0.0` | [0, 0.1]
  **What it does:** Creates new money each step. 70% flows to bank
  reserves (enabling lending), 30% to 'sys' (fiscal channel). At 3%
  rate + 3× banking multiplier: total money supply grows ~3.1% over
  20 years (vs +0.16% in the original implementation that just inflated
  sys balance).
  **Why it exists:** Money creation is how central banks expand the
  money supply. The original implementation (`sys += deposits × rate`)
  was a dead end — new money inflated a static balance and never
  circulated. The redesigned version uses the banking multiplier:
  new bank reserves → loans to businesses → wages → deposit multiplier.
  **Data:** McLeay, Radia & Thomas (2014) "Money creation in the modern
  economy." Bank of England Quarterly Bulletin.

### 9.2 `reserve_requirement` = `0.0` | [0, 1]
  **What it does:** Fraction of bank deposits that must be held as
  reserves. A real central-bank policy lever. At 0.10 (typical Basel III):
  10% of deposits are reserved, 90% can be lent. Lower requirements
  → more lending → more capital investment → more business growth.
  Only active when there is a positive bank balance.
  **How it fits:**
  - `reserve_requirement = 0.20`: banks lend 80% of deposits
  - Investment rate boost: `INVESTMENT_RATE × (1 + (1 – RR) × 0.02)`
  - Money creation lending pool: `deposits × (1 – reserve_requirement)`
  **Why it exists:** Fractional-reserve banking is a core monetary
  mechanism through which banks create money by lending deposits.
  Central banks directly set reserve requirements. The old
  `banking_multiplier` was an endogenously-determined ex-post identity
  (M/B ratio), not a parameter a central bank can set — it conflated
  cause and effect. `reserve_requirement` is a real policy lever with
  direct empirical grounding.
  **Data:** Basel III capital requirements (BCBS 2011). Standard
  fractional-reserve theory. McLeay, Radia & Thomas (2014) \"Money
  creation in the modern economy.\" Bank of England Quarterly Bulletin.
  **Legacy fallback:** `banking_multiplier` is still supported as an
  alias that multiplies deposits by `bnk × 0.01` when setting the
  lending pool, but defaults to 0 (OFF). Set `reserve_requirement`
  for causal control.

### 9.3 `interest_rate` = `0.005` | [0, 0.1]
  **What it does:** Interest rate on bank deposits. Determines how much
  workers earn on their cash savings held in the banking system.
  **Heritage:** Phase 6.

---

## 10. CORRUPTION & ENFORCEMENT (4 keys)

### 10.1 `corruption_level` = `0.0` | [0, 1]
  **What it does:** Reduces effective tax collection. At 0.40: 16% of
  tax revenue is lost to corruption (clk = 1 - 0.4 × 0.4 = 0.84).
  Also generates penalties for detected corruption.
  **Why it exists:** Corruption reduces government effectiveness and
  increases inequality by allowing the wealthy to avoid taxes.
  **Data:** Transparency International CPI.

### 10.2 `enforcement_quality` = `1.0` | [0, 1]
  **What it does:** Quality of legal enforcement. Affects court judgments
  (probability of plaintiff victory) and corruption detection.
  **Heritage:** Phase 4.

### 10.3 `detection_probability_base` = `0.5` | [0, 1]
  **What it does:** Base probability of detecting corruption or evasion.
  **Heritage:** Phase 4.

### 10.4 `information_asymmetry` = `0.0` | [0, 1]
  **What it does:** Degree of information asymmetry in insurance markets.
  Increases adverse selection: high-risk agents buy more insurance,
  low-risk agents buy less.
  **Heritage:** Phase 2.

---

## 11. FEATURE TOGGLES (6 keys)

### 11.1 `use_adversarial` = `False` | bool
  Enables adversarial behavior layer (strategic evasion, court gaming).
  **Phase 3.**

### 11.2 `use_events` = `False` | bool
  Enables shock events (natural disasters, recessions, mass torts).
  Demands a demand shock multiplier of 0.85 at event step.

### 11.3 `use_worker_coop` = `False` | bool
  Enables worker cooperative distribution of retained earnings.
  Workers receive profit shares when their firm is profitable.

### 11.4 `use_pooled_insurance` = `False` | bool
  Enables guild-based mutual insurance pools (alternative to private
  insurance).

### 11.5 `use_families` = `False` | bool
  Enables family/household tracking. Children inherit parent wealth,
  family-level Gini is computed.

### 11.6 `wire_lvt_evasion` = `False` | bool
  Enables LVT-specific evasion strategies (concealment, under-assessment).

---

## 12. OTHER (3 keys)

### 12.1 `economies_of_scale` = `0.0` | [0, 1]
  **What it does:** Larger businesses get higher TFP. Each 2× increase
  in capital above $50,000 adds `eos × ln(2)` to effective TFP.
  At 0.15: a business with 2× more capital gets 0.10 higher TFP.
  **Why it exists:** Returns to scale favor larger firms. This concentrates
  market power and contributes to inequality.
  **Heritage:** Phase 4.

### 12.2 `monopoly_markup_max` = `1.3` | [1, 2]
  **What it does:** Maximum markup over competitive price. Larger firms
  (higher market share) charge higher markups. At 1.3: max 30% markup.
  **Heritage:** Phase 4.

### 12.3 `carbon_tax_rate` = `0.0` | [0, 0.05]
  **What it does:** Tax on business revenue proportional to carbon
  intensity. Revenue to 'sys'. At 0.03 (Nordic): 3% of revenue taxed.
  **Heritage:** Phase 8b.

---

## 13. CONSTITUTIONAL & AUTO-ADAPTIVE (1 key)

### 13.1 `constitutional_amendment_rate` = `0.0` | [0, 0.05]
  **What it does:** Probability per year that a random policy parameter
  (tax rate, minimum wage, enforcement quality, corruption level)
  drifts by ±0.01. At 0.02: 2% chance per year of a random policy shift.
  **Why it exists:** Models the evolutionary dynamics of policy over time.
  Constitutional rules that are harder to amend (lower rate) produce
  more stable policy environments.

---

## 14. CRITICAL FIX: Business Profit Calibration

**Bug discovered during Iteration 1 of Phase 8c development:**
The production function used `L=8` as the labor input:
```python
rev = etfp × K^0.3 × 8^0.7 × markup
```
This produced revenue ~$200/step per business, while BUSINESS_WAGE_BILL
was $5000/step. All 10 businesses lost money every step. Every mechanism
dependent on business profit (capital income concentration, corporate tax,
retained earnings) was dead code.

**Fix:** Changed `(8 ** 0.7)` to `(750 ** 0.7)`:
- 8/10 businesses profitable (2 smallest marginal — realistic)
- Total after-tax profit: ~$14,500/step
- Revenue: ~$6,000-12,000/step for average business
- Profit margin: 15-50% depending on capital

L=750 was calibrated using: `L^0.7 = BUSINESS_WAGE_BILL / (A × K^0.3 × markup)`
for the average business, ensuring positive but moderate profit.

**Backward compatibility:** Gini values unchanged by ±0.0001 with all
mechanisms OFF. Total wealth conserved at $507,568,628.

**Justification:** The original L=8 was a placeholder. L=750 aligns the
Cobb-Douglas production function (α=0.3 standard from national
accounting) with the actual wage bill.

---

## Summary: All 57 Config Keys

| Category | Keys | Count |
|----------|------|:-----:|
| 1. Tax System | tax_type, lvt_rate, income_tax_rate, use_progressive_tax, top_marginal_surcharge, corp_tax_rate, vat_rate, use_vat, welfare_rate, admin_overhead | 10 |
| 2. Labor Market | skill_premium_growth, union_coverage, union_premium, capital_income_share, import_competition, minimum_wage, wage_ratio_cap, labor_supply_elasticity, tax_efficiency_loss | 9 |
| 3. Informal Labor | informal_share, informal_wage_penalty | 2 |
| 4. Wage Determination | education_variance, wage_dispersion_mult | 2 |
| 5. Asset Concentration | capital_income_concentration, capital_income_top_share, housing_wealth_concentration, patrimonial_wealth | 4 |
| 6. Income Effects | income_effect_labor, elite_capture_intensity, cpf_rate | 3 |
| 7. Institutional | financial_services_premium, reunification_shock, hartz_reform, child_benefit_taper, education_gdp_share, healthcare_gdp_share | 6 |
| 8. Inheritance | inheritance_rate, inherit_bequest | 2 |
| 9. Monetary | money_creation_rate, reserve_requirement, interest_rate | 3 |
| 10. Enforcement | corruption_level, enforcement_quality, detection_probability_base, information_asymmetry | 4 |
| 11. Feature Toggles | use_adversarial, use_events, use_worker_coop, use_pooled_insurance, use_families, wire_lvt_evasion | 6 |
| 12. Other | economies_of_scale, monopoly_markup_max, carbon_tax_rate | 3 |
| 13. Constitutional | constitutional_amendment_rate | 1 |
| 14. Business Profit | L=750 fix (not a key, but documented) | 1 |
| **Total** | | **56** |

28 Phase 8 mechanisms (new or modified), 28 inherited from Phases 4-6.
All 56 are config-driven. All default OFF/0/1 unless noted.
Zero per-country code. All parameterized from real data.

---

## Appendix A: Audit Results & Fixes

### Audit Findings (June 2026)
All 57 mechanisms were audited by independent subagents evaluating each
against economic theory and empirical data. Results:
- **46 JUSTIFIED** — strong theory + empirical data support
- **2 UNCERTAIN** — TFP_TAX_ELASTICITY, banking_multiplier (identification issues)
- **1 ARBITRARY** — wage_ratio_cap (no country has enacted binding caps)
- **1 UNSCALED** — use_progressive_tax brackets not scaled to simulation income

### Fixes Applied

#### Fix 1: `use_progressive_tax` — brackets scaled to simulation income
**Before:** Fixed US-dollar brackets ($20k-$200k) — all workers in 10% bracket.
The function had a hardcoded default `median_annual=300.0` fallback.
**After:** Brackets computed as fractions of median simulation income.
`median_annual` is now a REQUIRED parameter (no default) computed dynamically
from the population's actual median wage at step 1 of the simulation.
Brackets: 10%: 0 to 0.44×median, 15%: 0.44-1.11×median, 25%: 1.11-2.22×median,
35%: 2.22-4.44×median, 40%: 4.44+×median
**Result:** $10/hr→10%, $25/hr→12.8%, $40/hr→16.7% (was flat 10%)
**Data:** US 2020 IRS brackets as ratios of median income ($45,000).
**Validation:** Both `tax_efficiency_loss` and `reserve_requirement` now have
range checking with warnings for values outside [0,1]. All legacy fallback
paths verified: TFP_TAX_ELASTICITY=-0.3 changes NW_Gini by -0.0388;
banking_multiplier=5 with bank reserves produces 0.31% mean delta.

#### Fix 2: `banking_multiplier` → `reserve_requirement`
**Before:** `banking_multiplier` — an ex-post identity (M/B ratio), not a
behavioral parameter. No central bank directly sets the multiplier.
**After:** `reserve_requirement` — fraction of deposits banks must hold as
reserves (0-1). A real policy lever. Default 0.
**Data:** Basel III capital requirements; standard fractional-reserve theory.

#### Fix 3: `wage_ratio_cap` → `top_marginal_surcharge`
**Before:** `wage_ratio_cap` — CEO-to-worker pay ratio limit. No country
has enacted a binding cap; the parameter had zero empirical grounding.
**After:** `top_marginal_surcharge` — additional tax rate on top earners
(sorted by wealth percentile). At 15% on top 20%: Gini reduces by -0.019.
**Data:** US ACA 0.9% surtax, UK 45% additional rate, France 75% millionaire
tax (2013-2014), US historic top rates (70-91% through 1960s-70s).
Piketty-Saez-Zucman top income data.

#### Fix 4: `TFP_TAX_ELASTICITY` → `tax_efficiency_loss`
**Before:** `TFP_TAX_ELASTICITY` — suffers from severe endogeneity
(taxes and TFP are jointly determined by common factors).
**After:** `tax_efficiency_loss` — Harberger excess burden parameter.
DWL = 0.5 × efficiency_loss × t². Clean identification from compensated
elasticity η, well-estimated at ~0.3-0.5 (Chetty 2012).
**Data:** Harberger, A. (1964) "Taxation, resource allocation, and welfare."
Chetty, R. (2012) "Bounds on elasticities with optimization frictions."

All fixes backward-compatible (default OFF, legacy fallbacks preserved).
Baseline Ginis unchanged (±0.0001).

### Deep Fix: `TFP_TAX_ELASTICITY` default changed from -0.15 to 0.0
**Before:** Default value was the imported constant `TFP_TAX_ELASTICITY = -0.15`
(from comparison_phase4.py). Although `tax_efficiency_loss` replaced it, the
legacy fallback code (`elif tfp_elast != 0:`) was ALWAYS active because
`tfp_elast` defaulted to -0.15 — making `tax_efficiency_loss` dead code unless
explicitly set.
**After:** `TFP_TAX_ELASTICITY` defaults to 0.0. The legacy fallback only
activates if a config explicitly writes `TFP_TAX_ELASTICITY: -0.3`. The new
`tax_efficiency_loss` (default 0) is now the only active path when configured.
**Verification:** All-OFF runs produce identical revenue (legacy path skipped).

### Deep Fix: `banking_multiplier` code paths all replaced with `reserve_requirement`
**Before:** `banking_multiplier` was removed from documentation but still had
active code paths in (1) investment rate calculation: `INVESTMENT_RATE × (1 + bnk × 0.05)`,
and (2) money creation lending pool: `min(0.8, bnk × 0.5)`.
**After:** Both code paths now use `reserve_requirement`:
- Investment rate: `INVESTMENT_RATE × (1 + (1 – RR) × 0.02)` when RR > 0
- Lending pool: `deposits × (1 – reserve_requirement)`
The legacy `bnk` variable still exists but defaults to 0 and only acts as a
last-resort fallback in the banking section core (line 622).
**Verification:** All-OFF runs produce identical lending (RR=0 → no lending).

### Deep Fix: `wage_ratio_cap` scope clarified (coop-only, not general)
**Before:** `wage_ratio_cap` was replaced by `top_marginal_surcharge` as a
general progressive tax, but the old key remained active for worker cooperative
distribution (line 419: `mt = min_wage × wrc`). No documentation explained this
was coop-specific.
**After:** Section 2.7 in MECHANISMS.md now explicitly documents
`wage_ratio_cap` as a **cooperative governance parameter** (only active when
`use_worker_coop=True`). The general-use replacement (`top_marginal_surcharge`)
is documented as Section 1.5 in the Tax System category.
**Verification:** Coop-disabled configs (the default) never reach the code path.

### Closed-System Limitation: DWL as Distribution, Not Destruction
The `tax_efficiency_loss` mechanism computes a Harberger deadweight loss
that reduces business revenue before profit calculation. In an open
economy, this DWL would reduce total output (GDP). In the closed-system
simulation (total wealth ~$507M conserved), DWL cannot destroy money —
it instead redistributes from business profits (capital income) to the
system balance (government/tax revenue). The NW_Gini sensitivity test
confirms this: DWL=1.0 at 50% income tax changes net worth Gini from
0.3025 to 0.2687 while total wealth stays at $507,392,851.
**Impact:** DWL correctly reduces capital income concentration and
business investment but does NOT reduce total wealth. This is a
documented closed-system constraint, not a flaw in the Harberger
formula. Future open-system versions with money creation/destruction
will properly model the aggregate output loss.



---

## 11. IMPORT DISPLACEMENT — Sectoral Reallocation (3 keys)

### 11.1 `import_displacement_rate` = `0.0` | [0, 1]
**What it does:** Sectoral reallocation rate for bottom-half workers exposed to import competition. Displaced workers' wages drop to 70%.

**Why it exists:** Direct wage cuts from import competition are small; the dominant inequality channel is job displacement (Autor, Dorn & Hanson 2013).

### 11.2 `import_disp_intensity` = `0.1` | [0, 1]
**What it does:** Multiplier on displacement probability. Monthly prob = min(1.0, import_comp × rate × intensity).

### 11.3 `min_wage_floor` = `10.0` | [0, ∞)
**What it does:** Minimum hourly wage floor for displaced workers. Configurable per country.

### 11.4 Validation
16 unit tests PASS. Wage ratio = 0.7x (20/20 events). All 9 backtests PASS (default OFF).


### 11.4 `import_disp_recovery_rate` = `0.003` | [0, 1]
**What it does:** Monthly wage recovery rate for displaced workers. Each step, a displaced worker's wage moves toward their pre-displacement wage target by this fraction of the remaining gap.

**Why it exists:** Without recovery, displacement produces permanent wage losses that compound over long simulations (Gini=0.97 at 480 steps). With 0.3% monthly recovery, wages recover ~33% of the gap over 5 years, matching empirical evidence from Jacobson, LaLonde & Sullivan (1993) and Couch & Placzek (2010).

**Calibration:** 0.003/month → after 5yr (60 steps), ~16% of wage gap closed. After 10yr (120 steps), ~30% closed. Displaced workers remain measurably below trajectory but not permanently trapped.
