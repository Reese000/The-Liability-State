# Adversarial Strategy Library

**Purpose**: This document catalogs every way an agent in the Liability State simulation can exploit the system. Each strategy is a pre-programmed behavior the Strategy Controller can switch to when the expected value of exploitation exceeds honest behavior. The simulation tests whether the LS can self-correct when agents exploit it.

**Document Status**: Living specification — update as new strategies are discovered during simulation runs.

---

## Strategy Selection Logic

The Strategy Controller evaluates the following per agent per step:

```
For each strategy S that meets prerequisites:
    eV(S) = P(success) × reward(S) + P(failure) × penalty(S)
            + P(detection) × detection_penalty(S)
            + non_monetary_factor(S)
    
    Apply honesty discount: eV(S) *= agent.honesty if S != 'honest'
    
    If eV(S) > eV(honest) × (1 + agent.inertia):
        agent switches to strategy S
```

**Key parameters**:
- `agent.honesty` (0-1): Moral multiplier on exploitative actions
- `agent.inertia`: Threshold for switching (represents effort of change)
- `concealment_investment`: Modifier that reduces P(detection) for sophisticated agents

---

## 1. PREMIUM EVASION

### 1.1 Risk Under-Reporting

**Mechanic**: Agent truthfully declares a risk profile lower than their actual risk exposure to obtain a cheaper insurance premium.

**Prerequisites**:
- Agent holds an active insurance policy
- Agent's actual risk level exceeds declared risk level
- Realistic concealment mechanism exists (no mandatory telematic monitoring)

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Insurer audit frequency | +0.10 per audit per period |
| Gap between declared and actual risk | +0.15 per risk decile gap |
| Agent concealment investment | -0.05 per unit concealment |
| Glass Box transparency level | +0.10 per tier |
| Prior claims history mismatch | +0.20 if past claims exceed declared profile |

Base detection probability: `P_detect = 0.15 + 0.15 × risk_gap - 0.05 × concealment + audit_modifier + history_modifier`

**Expected Value Calculation**:

```
eV = (premium_savings × steps_until_audit) × (1 - P_detect)
     - P_detect × (back_premiums + penalty_multiplier × premium_savings + rate_increase)
```

Where:
- `premium_savings` = honest_premium - declared_premium
- `steps_until_audit` = expected number of steps before audit
- `back_premiums` = premiums owed for the under-payment period
- `penalty_multiplier` = 2.0 (standard), 3.0 (if fraud pattern detected)
- `rate_increase` = present value of all future premium increases

**System Detection**:
1. **Actuarial audit**: Insurer compares declared risk to observed claim frequency. Statistical outlier detection flags agents in the top decile of claim-to-premium ratio.
2. **Competitor tip**: Rival insurer or whistleblower spots inconsistency and reports for bounty.
3. **Accident investigation**: When a claim is filed, actual risk exposure is measured. Gap triggers retroactive premium adjustment.
4. **Actuarial Commons cross-check**: Public risk models flag agents whose declared profile diverges from similar agents in their cohort.

**System Response**:
1. First offense: Back premiums owed + 2× penalty + premium increase to honest rate + 10%
2. Second offense: Back premiums + 3× penalty + premium increase to honest rate + 25% + flagged in Reputation Database
3. Third offense: Policy cancelled, blacklisted period, mandatory high-risk pool placement at 300% base rate

### 1.2 Selective Omission (Partial Disclosure)

**Mechanic**: Agent reveals multiple risk factors but omits the most damaging ones (e.g., discloses minor driving violations but not a DUI).

**Prerequisites**:
- Information asymmetry between agent and insurer
- No mandatory comprehensive data-sharing protocol

**Detection Probability**:
- Lower than full under-reporting (P_detect ≈ 0.10 + 0.10 × significance_of_omission)
- Detected primarily through claim investigation after accident

**Expected Value Calculation**: Same structure as 1.1, with lower detection probability but higher penalty when caught (can be classified as fraud rather than negligence).

**System Response**:
- Treated as insurance fraud (see Section 2) when omission is material
- Retracted premium discount + punitive damages if claim is denied

---

## 2. INSURANCE FRAUD

### 2.1 Fabricated Claim

**Mechanic**: Agent files a claim for a loss that never occurred (staged accident, fake injury, invented theft).

**Prerequisites**:
- Agent has active insurance coverage for the claimed loss type
- Agent has ability to create plausible evidence (or colludes with a counterparty)

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Claim amount relative to policy limit | +0.10 per 10% of limit |
| Timing (claim filed just after policy purchase) | +0.25 if < 30 days |
| Prior claims frequency | +0.10 per claim in last 12 months |
| Evidence quality | -0.20 for strong evidence, +0.30 for weak |
| Forensic investigation capability of insurer | +0.15 per tier |
| Collusion with insider (e.g., doctor, repair shop) | -0.20 |
| Amount of claimed loss vs. statistical norm | +0.15 per standard deviation |

Base detection probability: `P_detect = 0.20 + timing_modifier + frequency_modifier - evidence_quality + investigation_tier`

**Expected Value Calculation**:

```
eV = (claim_payout × P_approval) × (1 - P_detect)
     - P_detect × (policy_cancellation + legal_penalties + fraud_marking)
     - (opportunity_cost of time spent on fraud)
```

Where:
- `P_approval` = probability claim is approved if undetected (depends on evidence quality)
- `legal_penalties` = counter-suit damages (3× claim amount under English Rule)
- `fraud_marking` = permanent reputation damage affecting all future insurance

**System Detection**:
1. **Claims investigation**: Adjuster reviews evidence, interviews witnesses, cross-references timelines.
2. **Reputation Database cross-reference**: Plaintiff's history of claims flagged.
3. **Forensic surveillance**: Sensor logs, camera footage, GPS data contradict claim.
4. **Statistical anomaly detection**: Claim amount, type, or timing is outlier for agent's cohort.

**System Response**:
1. Claim denied
2. Policy immediately cancelled
3. Agent blacklisted in shared Plaintiff Database
4. Counter-suit for fraud → 3× legal costs + damages (English Rule)
5. Criminal referral for perjury/fraud (if evidence strong)
6. Reputation damage affects all future insurance applications

### 2.2 Claim Inflation (Padding)

**Mechanic**: Agent has a legitimate claim but exaggerates the loss amount (e.g., $5K damage claimed as $15K).

**Prerequisites**:
- Agent has a real, insurable loss
- Ability to obtain inflated repair estimates

**Detection Probability**:
- Moderate (P_detect ≈ 0.25 + 0.10 × inflation_ratio)
- Depends on insurer's independent assessment capability

**Expected Value Calculation**:

```
eV = (extra_payout × P_approval) × (1 - P_detect)
     - P_detect × (full_claim_denial + penalties)
```

**System Response**:
- If inflation < 20%: Adjusted payout to true loss, warning on file
- If inflation > 20%: Full claim denied, policy reviewed, possible fraud charges

### 2.3 Double-Dipping (Multiple Policies)

**Mechanic**: Agent takes out the same coverage from multiple insurers (or multiple policies from the same insurer) and files claims for the same loss with each.

**Prerequisites**:
- Three-Source Mandate means multiple policies are normal — creates cover for double-dipping
- Insurers do not share real-time claims data

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Number of policies claiming same loss | +0.15 per extra policy |
| Timing synchrony | +0.20 if claims filed within 48 hours |
| Insurer data-sharing agreement exists | -0.30 if no sharing, +0.20 if sharing |
| Amount consistency across claims | +0.15 if amounts are identical |

Base detection probability: `P_detect = 0.10 + 0.15 × extra_policies + timing_modifier - data_sharing + amount_modifier`

**Expected Value Calculation**:

```
eV = (total_claim_payouts - actual_loss) × (1 - P_detect)
     - P_detect × (all_claims_denied + fraud_penalties + loss_of_all_policies)
```

**System Detection**:
1. **Cross-insurer database**: Actuarial Commons runs periodic checks for claims on same loss event from different insurers.
2. **Claims adjuster communication**: Adjusters from different insurers for same loss coordinate.
3. **Policy overlap audit**: Random audits detect same-loss-date across policies.

**System Response**:
- All claims denied
- All policies cancelled
- Blacklisted from all insurers in the system
- Referred for fraud prosecution

---

## 3. HARBERGER GAMING

### 3.1 Land Value Under-Declaration

**Mechanic**: Agent declares their land at below true market value to reduce LVT liability, accepting the risk of forced sale at the low price.

**Prerequisites**:
- Agent owns land on Harberger registry
- Agent has low sentimental attachment to the land (willing to sell at declared price)
- No prior bids at higher valuations

**Detection Probability**: Self-enforcing (anyone can buy at declared price).

| Factor | Effect on forced sale probability |
|--------|----------------------------------|
| Gap between declared and true value | +0.05 per 10% gap |
| Number of potential buyers in area | +0.10 per log unit |
| Development pressure (land demand) | +0.15 per tier |
| Option Premium penalty phase active | -0.15 (buyers face 15% refusal penalty) |
| Agent's prior lowball history | +0.10 per prior low-declaration period |

**Expected Value Calculation**:

```
eV = (lvt_savings_per_step × expected_holding_steps) × P(no forced_sale)
     - P(forced_sale) × (property_value_true - sale_proceeds)
     + [if forced sale: relocation_costs + business_disruption]
```

Where:
- `P(no forced_sale)` = 1 - P(forced_sale) where forced_sale probability depends on market conditions
- `lvt_savings_per_step` = (true_value - declared_value) × lvt_rate
- `expected_holding_steps` = expected steps before forced sale attempt

**System Detection** (market-based, not algorithmic):
1. **Buyer bid**: Any agent sees the low declared price and can post a bond to purchase.
2. **Competitor bid**: Rival business or speculator spots the arbitrage.
3. **Option Premium trigger**: After 14-day free window, buyer can force sale; owner pays 15% to refuse.

**System Response**:
1. **Market response**: Land is purchased at declared price → agent loses land
2. **Refusal penalty**: Agent pays 15% of offer price + tax basis raised to offer price
3. **Repeated pattern**: If agent repeatedly under-declares and refuses, flagged for "Harberger gaming" — reputation damage, insurers may view as risk indicator

### 3.2 Collusive Under-Declaration (Side-Deal Gaming)

**Mechanic**: Two or more agents collude: A under-declares land value, B bids to force sale, A pays B a side payment to refuse/withdraw. They split the LVT savings.

**Prerequisites**:
- Two agents willing to collude (trust or smart contract)
- Side payments can be hidden (off-ledger, or through opaque mechanism)
- Both agents have capital to post bonds and make side payments

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Same-party repeat pattern | +0.25 if same buyer-seller pair repeatedly |
| Timing pattern (bid immediately after declaration) | +0.20 |
| Side payment detection (off-ledger detection) | +0.15 (requires investigation) |
| Number of colluding pairs | +0.05 per pair beyond first |
| Sophistication of concealment | -0.10 per unit |

Base detection probability: `P_detect = 0.15 + repeat_pattern + timing_anomaly - concealment`

**Expected Value Calculation**:

```
eV_each = (lvt_savings / 2) × steps_before_detection × (1 - P_detect)
          - P_detect × (back_taxes + antitrust_penalties + property_forfeiture_risk)
```

Where:
- `lvt_savings` = total LVT reduction achieved by collusion
- `antitrust_penalties` = treated as market manipulation (see Section 6)
- `property_forfeiture_risk` = possible if classified as "Systemic Sabotage"

**System Detection**:
1. **Pattern analysis**: Actuarial Commons detects repeated same-buyer/same-seller bid-refusal cycles.
2. **Transaction tracing**: Follows money to detect side payments.
3. **Whistleblower**: One colluder reports the other for bounty.
4. **Statistical outlier**: Property transitions or bid-refusal rates far above market normal.

**System Response**:
1. Tax basis forcibly set to estimated true value
2. Back taxes owed with 2× penalty
3. Antitrust penalties if classified as market manipulation
4. Both agents flagged in Reputation Database

### 3.3 Option Premium Griefing

**Mechanic**: A wealthy agent repeatedly posts bids on a target's land, forcing them into the penalty phase where they must pay 15% of the offer price to refuse. Used to bleed a competitor dry.

**Prerequisites**:
- Wealthy agent with capital to post bonds (tied up for 104 days max)
- Target owns valuable land
- Target cannot easily sell (sentimental/business-critical location)

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Pattern of repeated bids on same target | +0.30 after 2nd attempt |
| Bid price pattern (escalating or oscillating) | +0.15 |
| Market relationship (competitor → competitor) | +0.20 |

Base detection probability: `P_detect = 0.20 + repeat_pattern + relationship_modifier`

Note: The Option Premium is *designed* to make griefing expensive for the bidder (capital locked, 15% penalty paid to the target). Griefing is self-limiting — the bidder loses money on each failed attempt.

**Expected Value Calculation**:

```
eV_griefer = -(bond_opportunity_cost + penalty_if_refused) 
             + P(success) × (property_value_subsidized)

eV_griefer is almost always negative — this is a spite strategy, not a profit strategy.
```

**System Detection**:
1. Repetition triggers flagging on the Public Ledger
2. Court may find "abuse of process" if pattern continues

**System Response**:
- Market-based: Griefer loses the 15% penalty payment each cycle
- Legal: Target can sue for tortious interference if pattern is harassment
- Court can order bond forfeiture to victim

### 3.4 Harberger Price Collapse (Coordinated Devaluation)

**Mechanic**: A cartel of agents simultaneously declares all their properties at near-zero values, crashing the LVT tax base and the Land Value Index, aiming to destabilize the system or force a bailout.

**Prerequisites**:
- Cartel controls a significant fraction (>20%) of land in a compact
- Coordinated action among members (requires trust or enforceable smart contract)
- Acceptance that some properties will be purchased at low prices

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Synchronous declaration change | +0.40 if >50% of cartel declares within same step |
| Magnitude of drop | +0.30 if average declared value drops >50% |
| LVI deviation from trend | +0.25 |

Base detection probability: `P_detect = 0.50 + synchrony_modifier + magnitude_modifier`

**Expected Value Calculation**:

```
eV_cartel_member = (lvt_savings × tax_reduction_period) 
                   + (gain_from_buying_neighbors_at_low_price)
                   - P(detection) × (antitrust_penalties + cartel_disintegration + loss_of_properties)
                   - (value of properties lost to outside buyers)
```

**System Detection**:
1. **LVI anomaly**: Actuarial Commons detects Land Value Index drop that exceeds any economic fundamental.
2. **Coordinated declaration audit**: Statistical analysis flags synchronous changes.
3. **Market reaction**: Outside buyers rush to buy declared properties.

**System Response**:
1. Emergency LVT assessment at prior-period declared values (constitutional circuit breaker)
2. Full forensic audit of all cartel members
3. Antitrust charges — "Systemic Sabotage" classification → total asset forfeiture
4. Cartel members permanently banned from Harberger registry

---

## 4. COURT FLOODING

### 4.1 Frivolous Mass Litigation

**Mechanic**: Agent files many low-merit lawsuits hoping for nuisance settlements from defendants who prefer paying $5K rather than $50K in legal fees.

**Prerequisites**:
- Agent has capital for filing fees and litigation bonds
- Target defendants have deep pockets (businesses, insurers)
- English Rule (loser pays) is in effect — must be accounted for

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Cases filed per step | +0.10 per case beyond 1 |
| Win rate | +0.30 if win rate < 10% |
| Settlement percentage | +0.20 if >80% settled before adjudication |
| Amount claimed vs. settlement received | +0.25 if settlement < 10% of claimed |

Base detection probability: `P_detect = 0.15 + case_volume + win_rate_modifier + settlement_pattern`

**Expected Value Calculation**:

```
eV = Σ(cases)[ P(settlement) × settlement_amount × (1 - P_litigation_bond_lost) ]
     - Σ(cases)[ P(adjudicated_loss) × (filing_fee + defendant_legal_costs + litigation_bond_forfeit) ]
     - Σ(cases)[ P(anti_suit) × counter_claim_damages ]
     - reputation_damage × future_case_success
```

Key constraint: Under strict English Rule, a single loss with a well-funded defendant can result in $100K+ in liability, wiping out gains from many nuisance settlements.

**System Detection**:
1. **Plaintiff Database tracking**: Shared repository flags serial filers with low win rates.
2. **Court-level pattern detection**: Judge identifies same plaintiff filing similar claims.
3. **Insurer monitoring**: Insurers track who their policyholders are being sued by, cross-reference across policyholders.
4. **Attorney gatekeeping**: Lawyers must certify cases have merit; repeated false certification = malpractice.

**System Response**:
1. **Litigation bond requirement increase**: Courts raise bond minimum for flagged plaintiffs.
2. **Anti-suit injunction**: Court orders plaintiff to post bond for defendant's estimated legal costs before filing more cases.
3. **Summary judgment**: Pattern of frivolous cases → judge dismisses with prejudice.
4. **Counter-suit**: Defendant sues for abuse of process → 3× legal costs.
5. **Reputation database entry**: All future lawsuits by this plaintiff are viewed skeptically; burden of proof shifts.

### 4.2 Strategic Discovery Abuse

**Mechanic**: Agent files a legitimate lawsuit but uses discovery requests to impose massive compliance costs on the defendant, forcing settlement.

**Prerequisites**:
- Agent has filed a non-frivolous claim
- Discovery is broad enough to be burdensome
- Defendant has limited resources to respond

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Discovery cost / dispute value ratio | +0.20 if ratio > 2:1 |
| Number of document requests | +0.15 per 1,000 requests |
| Relevance of requested materials | +0.25 if < 20% relevant |

**Expected Value Calculation**:

```
eV = P(settlement) × (settlement_amount - filing_costs)
     - P(sanction) × (defendant_discovery_costs + court_penalties)
```

**System Detection**:
- Court monitors discovery proportionality
- Defendant files protective order
- Judge assesses whether discovery is "reasonably calculated to lead to admissible evidence"

**System Response**:
- Court limits discovery scope
- Costs shifted to plaintiff for abusive requests
- Sanctions for bad faith discovery

### 4.3 Grievance Re-Filing (Case Recycling)

**Mechanic**: Plaintiff files case, loses on merits, dismisses without prejudice before final judgment, re-files in a different court, hoping for a different outcome.

**Prerequisites**:
- Multiple courts with overlapping jurisdiction
- No centralized case tracking (or plaintiff exploits gaps)
- Defendant must incur legal costs repeatedly

**Detection Probability**:
- High if courts share data (P_detect ≈ 0.40 per re-file)
- Low if courts are independent (P_detect ≈ 0.10 per re-file)

**System Response**:
1. Preclusion: After 2 dismissals, court enters judgment with prejudice
2. Costs shifted to plaintiff for all prior filings
3. Court issues anti-suit injunction barring re-filing

---

## 5. GUILD RENT-SEEKING

### 5.1 Closed Shop / Membership Restriction

**Mechanic**: Guild restricts membership below market demand (artificial scarcity) to raise wages for existing members.

**Prerequisites**:
- Guild controls certification for a skill/occupation
- Guild has authority to set membership criteria
- Demand for the skill exceeds supply

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Wage premium for guild members vs. non-members | +0.20 per 20% premium |
| Membership growth rate vs. industry growth | +0.25 if membership grows slower |
| Certification pass rate | +0.20 if < 50% pass rate persists |
| Complaints from unrepresented workers | +0.15 per complaint type |
| New guild formation rate in same industry | -0.10 per competitor guild |

Base detection probability: `P_detect = 0.15 + wage_premium + growth_gap + pass_rate_modifier`

**Expected Value Calculation**:

```
eV = (member_wage_premium × member_count × period) 
     - (lost_dues_from_excluded_workers)
     - P(detection) × (antitrust_penalty + guild_liability_increase + certification_revocation)
```

**System Detection**:
1. **Labor market analysis**: Actuarial Commons detects wage premium inflation in guild-controlled professions.
2. **Competitor guild formation**: Unrepresented workers form rival guild, file suit for anti-competitive practices.
3. **Employer lawsuit**: Businesses that cannot find workers sue the guild for restraint of trade.
4. **Insurer assessment**: Guild mutual's risk profile elevated due to monopoly exposure.

**System Response**:
1. Court finding of restraint of trade → guild forced to relax membership criteria
2. Guild certification temporarily suspended by Actuarial Commons
3. Guild mutual's insurance premium raised (liability for anti-competitive harm)
4. Members can be held personally liable if guild is classified as a "cartel"

### 5.2 Certification Fee Extraction

**Mechanic**: Guild charges excessive certification fees that extract most of the wage premium, capturing the value of market power for guild leadership rather than members.

**Prerequisites**:
- Guild leadership is unaccountable to members
- Members have no exit option (no competing guild)
- Certification is mandatory for employment

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Fee-to-benefit ratio | +0.20 if fees > 30% of wage premium |
| Member complaints to Actuarial Commons | +0.10 per complaint |
| Leadership compensation vs. member wages | +0.25 if CEO > 10× median member |

**System Detection**:
- Member revolt or whistleblower
- External audit triggered by statistical anomaly

**System Response**:
- Guild charter reviewed and potentially revoked
- Members can sue guild leadership for fiduciary breach

### 5.3 Guild Quality Signaling Failure (Cheap Certification)

**Mechanic**: Guild certifies anyone who pays the fee without meaningful quality screening, degrading the signal value of certification while extracting dues.

**Prerequisites**:
- Guild has certification monopoly
- No external audit of certification standards

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Increase in certified member failures/defects | +0.30 per 10% increase |
| Employer complaints about certified quality | +0.15 per complaint |
| New certification standards compared to peer guilds | +0.25 if significantly lower |

**System Response**:
1. Guild mutual liability increases (more claims against certified members = higher premiums)
2. Employers form competing certification body
3. Court finds guild negligent in certification → liability for damages caused by substandard members

---

## 6. COLLUSION

### 6.1 Price-Fixing Cartel

**Mechanic**: Multiple businesses in the same industry agree to fix prices above competitive levels, sharing monopoly profits.

**Prerequisites**:
- Concentrated market (few competitors)
- Ability to monitor compliance with cartel agreement
- Mechanism for side payments or market allocation

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Market concentration (HHI) | +0.10 per 1,000 HHI points |
| Price variance among competitors | -0.20 if near-zero, +0.10 if high |
| Entry of new competitor | -0.10 (disturbs cartel) |
| Whistleblower among members | +0.40 if one member defects |
| At-least-one-honest-agent in market | +0.10 per honest agent |
| Price correlated across multiple independent cost inputs | +0.25 |

Base detection probability: `P_detect = 0.10 + concentration_modifier + price_variance_modifier + whistleblower_flag`

**Expected Value Calculation**:

```
eV = (cartel_profit - competitive_profit) × steps_persistent × (1 - P_detect)
     - P_detect × (antitrust_penalties + private_right_of_action_damages + reputation_loss)
```

Where:
- `antitrust_penalties` = 3× overcharges paid to customers + fines
- `private_right_of_action_damages` = any harmed party can sue for treble damages under LS antitrust law
- `reputation_loss` = future business partner trust erosion

**System Detection**:
1. **Price monitoring**: Actuarial Commons or market analysts detect price patterns inconsistent with competitive market.
2. **Whistleblower**: Cartel member defects for bounty (bounty = 10% of antitrust penalties collected).
3. **Customer complaint**: Buyers notice identical pricing across competitors.
4. **Statistical detection**: Price rigidity in face of input cost changes, price leadership patterns.

**System Response**:
1. Antitrust prosecution: 3× damages to all affected customers
2. Individual members personally liable (no corporate veil for antitrust)
3. Collusion classified as "High Crime of Systemic Sabotage" → total asset forfeiture
4. Permanent de-listing from Trust Ledger

### 6.2 Bid-Rigging / Market Allocation

**Mechanic**: Competitors agree not to compete in each other's territories or to rotate winning bids for contracts.

**Prerequisites**:
- Identifiable market segments or geographic territories
- Ability to monitor each other's bidding behavior

**Detection Probability**: Similar to 6.1, with additional modifiers for bid pattern analysis (+0.10 per suspicious rotation pattern).

**System Response**: Same as price-fixing, with additional contract voiding for affected deals.

### 6.3 Insurance Premium Collusion

**Mechanic**: Multiple insurers coordinate to maintain artificially high premiums, eliminating price competition.

**Prerequisites**:
- Concentrated insurance market (few major insurers)
- Actuarial Commons model usage is mandated (reduces differentiation — makes collusion easier)

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Premium variance across insurers | -0.30 if near-zero |
| Underwriting profit margin vs. historical | +0.20 if significantly above |
| New insurer entry | -0.15 (disrupts collusion) |

**System Detection**:
- Actuarial Commons detects pricing above what public risk models would produce
- Customers file antitrust suits
- New insurers undercut cartel pricing

**System Response**:
- Market share caps enforced (max 15% per compact)
- Criminal collusion penalties
- Affected policyholders receive treble damages

---

## 7. FORUM SHOPPING

### 7.1 Court Bias Exploitation

**Mechanic**: Agent selects a court (via contract clause or post-dispute choice) known to favor their type of party (plaintiff, defendant, corporate, individual).

**Prerequisites**:
- Multiple courts available with jurisdiction over the dispute
- Plaintiff has right to choose among whitelisted courts
- Court reputation/bias data is observable (public win-rate statistics)

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Win rate deviation from 50% | +0.25 per 10% deviation |
| Case volume at chosen court vs. alternatives | +0.15 if significantly lower |
| Plaintiff-defendant win rate gap at chosen court | +0.30 per 20% gap |
| Insurer whitelist status of chosen court | -0.20 if on whitelist |

Base detection probability: `P_detect = 0.10 + win_rate_deviation + volume_anomaly - whitelist_modifier`

Note: Forum shopping with pre-negotiated contract clauses is **legal** in LS unless the court is demonstrably biased. Detection leads to court-level consequences, not agent-level.

**Expected Value Calculation**:

```
eV = (expected_award_best_court - expected_award_worst_court) 
     - legal_cost_difference
     - P(court_audit) × (case_retransfer_cost + reputation_cost to chosen court)
```

**System Detection**:
1. **Win-rate statistics**: Actuarial Commons publishes per-court win rates by party type. Courts with extreme deviations are flagged.
2. **Insurer whitelist**: Insurers refuse to cover disputes in courts with bias patterns, limiting agent choice.
3. **Court-level sanctions**: Other courts may refuse to enforce judgments from demonstrably biased courts.

**System Response**:
1. Court flagged by Actuarial Commons → reputation damage → case volume drops
2. Insurer removes court from whitelist → no policy covers disputes there
3. If bias pattern persists, court's liability insurance becomes unaffordable → court dissolves

### 7.2 Cross-Compact Arbitrage

**Mechanic**: Agent files the same or related claims in multiple compacts, exploiting differences in damage valuation, environmental harm definitions, or procedural rules.

**Prerequisites**:
- Multiple compacts with overlapping jurisdiction
- Compact differences in damage caps, procedural rules, or evidence standards

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Same dispute filed in multiple compacts | +0.40 (automatic if cross-compact case tracker exists) |
| Compact win-rate differential | +0.20 if > 20% difference |

**System Response**:
1. First-filed rule: Court where case was first filed retains jurisdiction
2. STO (Supreme Trust Oracle) intervenes if forum shopping is flagrant
3. Judgments from compact-shopping are subject to cross-compact review

---

## 8. CONTRACT BREACH

### 8.1 Efficient Breach (Calculated Default)

**Mechanic**: Agent calculates that breaching a contract and paying damages is more profitable than performing.

**Prerequisites**:
- Agent has a binding contract
- Damages for breach are measurable and capped at expectation damages
- Agent has assets to pay damages if sued (or is judgment-proof)

**Detection Probability**:
- Automatic (counterparty knows they were harmed)
- P(detection) = 1.0 for the counterparty
- P(court_case) depends on whether suing is worth it for counterparty

**Expected Value Calculation**:

```
eV = (gain_from_breach) 
     - P(sued) × (damages + court_costs + reputation_damage)
     + risk_of_counterparty_self_help
```

Where:
- `P(sued)` = depends on counterparty's resources, likelihood of success, and amount at stake
- `damages` = expectation damages (what counterparty would have gained from performance) + legal costs

**System Detection** (by counterparty):
1. Counterparty experiences the breach directly
2. Counterparty evaluates: expected award > cost of litigation?
3. If yes, files court case

**System Response**:
1. Court orders expectation damages (value of promised performance)
2. English Rule: breaching party pays all legal costs if they lose
3. Reputation damage: future counterparties demand higher rates or collateral
4. Insurance premium increases (liability risk went up)

### 8.2 Strategic Default with Judgment-Proofing

**Mechanic**: Agent borrows or contracts knowing they will default, but has structured their affairs so no assets are reachable (shell company, assets in spouse's name, early distribution to shareholders).

**Prerequisites**:
- Agent has ability to move assets before judgment
- Legal entities can be structured with no assets (empty shell)
- Timing: assets moved before contract breach

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Asset movement proximity to breach | +0.30 if within 30 days |
| Entity complexity (shell layers) | +0.10 per layer |
| Insufficient remaining assets | +0.20 if < 10% of judgment value remains |
| KYC/KYA ledger compliance | -0.30 if ledger has full beneficial ownership |

Base detection probability: `P_detect = 0.20 + timing_modifier + entity_complexity - KYC_compliance`

**Expected Value Calculation**:

```
eV = (gained_value - assets_left_behind) × (1 - P_detect)
     - P_detect × (veil_piercing + personal_liability + fraud_charges)
```

**System Detection**:
1. KYC/KYA Ledger reveals beneficial ownership if properly maintained
2. Creditor sues to pierce corporate veil
3. Court examines timing of asset transfers (fraudulent conveyance)
4. Insurer investigates reasonable suspicion

**System Response**:
1. Veil pierced: shareholders/managers personally liable for judgment
2. Fraudulent conveyance reversal: assets clawed back
3. Criminal charges for fraud/concealment if pattern established
4. Harberger land title revocation if used for concealment

### 8.3 NDA Enforcement Abuse

**Mechanic**: Agent uses broad NDAs to suppress evidence of wrongdoing, then sues whistleblowers for breach of contract.

**Prerequisites**:
- Agent has employees/suppliers under NDA
- Wrongdoing exists that NDAs would conceal
- Jurisdiction has not yet voided NDA for fraud disclosure

**Detection Probability**:
- Low if NDAs are standard practice (P_detect ≈ 0.15)
- Detection comes from whistleblower who ignores NDA and reports to Actuarial Commons

**Expected Value Calculation**:

```
eV = (harm_concealed - potential_liability_if_exposed) × (1 - P_whistleblower_ignores_NDA)
     - (cost of defending NDA enforcement against statutory exemption)
```

**System Response**:
- Under LS whistleblower protections, NDAs that conceal evidence of fraud/public harm are void
- Counter-suit by whistleblower for wrongful NDA enforcement → treble damages
- Guild mutual bears secondary liability if it knew of suppression

---

## 9. POLLUTION / EXTERNALIZATION

### 9.1 Direct Environmental Harm

**Mechanic**: Agent causes pollution (emissions, waste dumping, resource depletion) without paying cleanup costs, externalizing the harm onto neighbors or the commons.

**Prerequisites**:
- Agent operates a business with pollution potential
- Pollution detection is imperfect (not all emissions are monitored)
- Victims must detect, prove causation, and sue

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Pollution type visibility | +0.30 visible (smoke, spill), -0.10 invisible (groundwater, air particulates) |
| Monitoring technology in area | +0.20 per sensor type present |
| Victim observability | +0.20 if victims are in immediate vicinity |
| Remote/isolated operation | -0.25 |
| Concealment investment | -0.10 per unit (dilution, night dumping, etc.) |

Base detection probability: `P_detect = 0.20 + visibility_modifier + monitoring_level + victim_proximity - concealment`

**Expected Value Calculation**:

```
eV = (pollution_cost_savings × steps_before_detection) × (1 - P_detect)
     - P_detect × (cleanup_cost + liability_damages + premium_increase + remediation_escrow)
```

Where:
- `pollution_cost_savings` = cost of proper disposal minus cost of illegal dumping
- `cleanup_cost` = actual environmental remediation (can be 10-100× savings)
- `liability_damages` = compensation to affected parties (medical bills, property damage)
- `premium_increase` = future insurance rate hike due to higher risk classification
- `remediation_escrow` = court may order funds held in escrow for future cleanup

**System Detection**:
1. **Victim discovery**: Neighbor notices dead fish, illnesses, discolored water.
2. **Monitoring sensors**: Air/water quality monitors detect anomalies; data is public.
3. **Insurer audit**: Insurer inspects facility, finds missing emissions controls.
4. **Competitor tip**: Rival business reports pollution for competitive advantage.
5. **Citizen scientist**: Public-led environmental monitoring (data submitted to Actuarial Commons).

**System Response**:
1. **Liability suit**: Victims file class action or individual suits under strict liability.
2. **Cleanup order**: Court orders remediation at polluter's expense.
3. **Premium surcharge**: Insurer imposes massive premium increase or cancels coverage.
4. **Rehabilitation**: If pollution is severe, business may be forced to cease operations until remediated.
5. **Criminal charges**: If intentional, classified as "Systemic Sabotage."
6. **Externality Vault**: Pollution fees diverted to restoration, removed from dividend pool.

### 9.2 Cross-Border Pollution (Compact Externalization)

**Mechanic**: Business in Compact A pollutes a resource shared with Compact B (downstream river, cross-border airshed). Compact B's victims must sue in Compact A's courts or navigate inter-compact dispute resolution.

**Prerequisites**:
- Shared resource between compacts
- Compact A has lax enforcement or court bias favoring local businesses

**Detection Probability**:
- Same as 9.1, but enforcement is harder (cross-compact barriers)
- P(detection) reduced by 0.10-0.30 depending on inter-compact friction

**System Response**:
- Default: Compact B victims sue in Compact A courts
- Escalation: Inter-compact dispute → STO backstop enforcement
- Compact A faces Trust Blockade if it refuses to enforce judgments

### 9.3 Long-Latency Harm Dumping

**Mechanic**: Agent disposes of substances that cause harm only after decades (carcinogens, persistent toxins), betting that the statute of limitations will expire or records will be lost.

**Prerequisites**:
- Access to long-latency hazardous materials
- Ability to dispose without immediate detection
- Time horizon longer than institutional memory

**Detection Probability**:
- Near-zero at time of dumping (P_detect ≈ 0.05)
- Potentially 1.0 decades later when harm manifests (if records exist)

**Expected Value Calculation**:

```
eV = (disposal_cost_savings × 100% probability now) 
     - [P(records_exist_in_future) × P(foreseeability_determined) × (future_liability_PV)]
```

In LS, **long-latency harm can be sued now**: If the substance is known to cause harm, the harm is foreseeable even if it hasn't manifested yet. Damages are calculated actuarially.

**System Response**:
- **Preventive suit**: Victims can sue now for actuarially-determined future harm
- **Knowledge cutoff**: If harm was unknown at time of dumping, no liability for past; but future dumping becomes strictly liable once knowledge is available
- LS Evolution Loop means standard of care shifts immediately upon knowledge publication

---

## 10. GLASS BOX VIOLATION

### 10.1 Data Concealment (Partial Transparency)

**Mechanic**: Agent provides incomplete or misleading data to the Glass Box system — omitting safety incidents, faking emissions logs, hiding asset ownership.

**Prerequisites**:
- Agent is subject to Glass Box Mandate (corporation, guild, court, or insurer)
- Agent can plausibly claim "technical error" or "oversight"
- Actuarial Commons auditing is imperfect

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Data inconsistency (internal vs. reported) | +0.25 per inconsistency |
| Competitor/whistleblower tip | +0.30 |
| Actuarial Commons random audit | +0.15 per audit cycle |
| Private Civil Servant warrant | +0.40 (deep audit finds everything) |
| Data gap magnitude | +0.20 per 10% of expected data missing |

Base detection probability: `P_detect = 0.10 + inconsistencies + whistleblower + audit_coverage + data_gap`

**Expected Value Calculation**:

```
eV = (harm_concealed_value × steps_before_exposure) × (1 - P_detect)
     - P_detect × (liability_for_concealed_harm + obstruction_penalties + loss_of_glass_box_status + reputation_collapse)
```

Where:
- `loss_of_glass_box_status` = most severe — without Glass Box status, the entity cannot operate legally
- `obstruction_penalties` = classified as "Strategic Sabotage" (criminal)
- `reputation_collapse` = insurers, counterparties, and customers all flee

**System Detection**:
1. **Data reconciliation audit**: Actuarial Commons compares internal logs (if accessed via PCS warrant) with public data.
2. **Whistleblower**: Employee reports concealment (protected, statutory NDA void).
3. **Competitor discovery**: Rival finds the hidden data through investigative auditing.
4. **PCS deep audit**: Random or suspicion-based Private Civil Servant inspection.

**System Response**:
1. Immediate liability for all harm that was concealed
2. Glass Box certification revoked → entity cannot operate
3. Personal liability for executives who authorized concealment
4. "Strategic Sabotage" classification → total asset forfeiture
5. Mandatory PCS audit of all operations for 5 years

### 10.2 Asset Invisibility (Ownership Concealment)

**Mechanic**: Agent hides ownership of assets through shell companies, nominee directors, or off-ledger arrangements to shield assets from liability judgments.

**Prerequisites**:
- Access to legal/trust structures that obscure beneficial ownership
- Jurisdictions with weak KYC/KYA enforcement

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Entity chain length | +0.05 per entity layer |
| KYC/KYA ledger compliance level | -0.30 if ledger is properly maintained |
| Hawala / crypto-based concealment | -0.20 (harder to trace) |
| Judgment enforcement attempt | +0.40 (creditor has incentive to trace) |

Base detection probability: `P_detect = 0.15 + entity_chain_length - KYC_level + enforcement_attempt`

**Expected Value Calculation**:

```
eV = (assets_protected_from_judgment) × (1 - P_detect)
     - P_detect × (asset_forfeiture + criminal_charges + total_personal_liability + loss_of_all_legal_shield)
```

**System Detection**:
1. **KYC/KYA Ledger**: Requires ultimate beneficial owner registration
2. **Judgment enforcement**: Creditor hires asset tracers, sues to pierce entities
3. **Private Civil Servant warrant**: Deep audit of corporate structure
4. **Financial tracing**: Banks/insurers report suspicious ownership patterns
5. **Whistleblower**: Associate reveals beneficial ownership

**System Response**:
1. All concealed assets forfeit to judgment creditors
2. Personal liability pierces all entities back to beneficial owner
3. Loss of all legal shield — unlimited personal liability for all business debts
4. Criminal charges for "Strategic Sabotage"
5. Permanent ban from holding Harberger titles or operating corporations

### 10.3 Actuarial Model Concealment

**Mechanic**: Insurer uses secret proprietary risk models alongside the mandated public Actuarial Commons model, using the private model for pricing while claiming to use the public one.

**Prerequisites**:
- Insurer has developed a superior predictive model
- Actuarial Commons mandates equal model usage
- Regulatory auditing is imperfect

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Pricing deviation from Actuarial Commons baseline | +0.20 per 10% deviation |
| Underwriting profit gap vs. competitors | +0.15 if significantly higher |
| Data scientist whistleblower | +0.40 |
| Internal model documentation discovered | +0.30 |

**System Response**:
- License revoked immediately
- Bond forfeited to Actuarial Commons
- All policies priced using secret model are voidable by policyholders
- Executive personal liability for fraud

---

## 11. LVT EVASION

### 11.1 Strategic Land Fragmentation

**Mechanic**: Large landholder subdivides land into many small parcels owned by different legal entities (family members, shell companies, trusts), each below the LVT assessment threshold or qualifying for exemptions.

**Prerequisites**:
- LVT has a minimum assessment threshold or small-parcel exemption
- Agent has many legal entities at their disposal
- Land can be subdivided without losing economic value

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Number of entities per acre | +0.20 if > 5 entities/acre |
| Ownership concentration (beneficial owner behind entities) | +0.25 if same beneficial owner |
| Parcel size pattern (all at threshold) | +0.30 if > 50% of parcels at minimum size |

Base detection probability: `P_detect = 0.15 + entity_density + concentration_pattern + threshold_clustering`

**Expected Value Calculation**:

```
eV = (lvt_savings_from_fragmentation) × (1 - P_detect)
     - P_detect × (back_taxes + penalties + forced_consolidation + beneficial_owner_prosecution)
```

**System Detection**:
1. **Beneficial ownership tracing**: KYC/KYA Ledger reveals common beneficial owner.
2. **Parcel pattern analysis**: Actuarial Commons detects suspicious subdivision patterns.
3. **Insurer flag**: Land insurance applications reveal same beneficial owner.

**System Response**:
1. Beneficial owner assessed as single entity for LVT purposes
2. Back taxes with 2× penalty
3. Entities consolidated for taxation
4. If fraudulent, criminal penalties

### 11.2 Vacancy Tax Evasion

**Mechanic**: Agent leaves property vacant but reports it as "occupied" by a nominal tenant (friend, relative, shell company) to avoid the triple-LVT vacancy penalty.

**Prerequisites**:
- Property is in area with vacancy tax
- Agent can create a plausible occupancy appearance (mail forwarding, occasional car in driveway)

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Utility usage (water/electricity) vs. occupied baseline | +0.30 if < 10% of normal |
| Vehicle/personnel presence evidence | +0.20 (neighbor reports, CCTV, delivery records) |
| Nominal tenant relationship | +0.20 if tenant is related entity |
| Random inspection | +0.15 per inspection cycle |

**System Response**:
- Triple LVT applied retroactively
- Penalty equal to 1 year of triple rate
- Nominal tenant liable as accessory if collusive

### 11.3 Compact LVT Arbitrage

**Mechanic**: Agent moves land holdings to compacts with lower LVT rates while continuing business operations in a higher-LVT compact, exploiting compact differentiation.

**Prerequisites**:
- Multiple compacts with different LVT rates
- Business can be legally separated from land ownership
- Migration costs are lower than LVT savings

**Detection Probability**: Low (this is generally legal — compact differentiation is by design)

**Expected Value Calculation**:

```
eV = (lvt_savings × period) - (migration_costs + operational_inefficiencies)
```

**System Response**: None — this is intended behavior. Compact competition on LVT rates is a feature, not a bug. The Exodus Equilibrium ensures compacts compete for capital.

### 11.4 Agricultural / Land-Use Misclassification

**Mechanic**: Agent registers non-agricultural land as agricultural to qualify for reduced LVT rates or exemptions.

**Prerequisites**:
- Agricultural land receives favorable LVT treatment
- Agent can plausibly claim agricultural use (nominal crop, a few animals)

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Agricultural revenue per acre | +0.30 if below threshold for genuine farming |
| Adjoining land uses | +0.15 if surrounded by non-agricultural |
| Crop/animal type | +0.20 if ornamental/minimal |
| Inspection | +0.20 per inspection cycle |

**System Response**:
- Reclassification + back taxes at non-agricultural rate for 3 years
- Penalty of 50% of back taxes
- Repeat offense: double penalty and land use restriction

---

## 12. SHELL COMPANY / LIABILITY SHIELDING

### 12.1 Insufficient Capitalization

**Mechanic**: Agent creates a corporation with minimal capital (thinly capitalized), conducts high-risk operations through it, and lets it bankrupt when liability hits, while the beneficial owner keeps profits.

**Prerequisites**:
- Limited liability structure (even under LS conditions)
- Separation between operating company and asset-holding entity
- Ability to extract profits regularly (dividends, management fees)

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Capital-to-risk ratio | +0.30 if capital < 10% of potential liability |
| Dividend payout ratio | +0.20 if > 80% of profits paid out |
| Debt-to-equity ratio | +0.25 if > 5:1 |
| Third-party credit assessment | +0.10 if insurer rates as high-risk |

Base detection probability: `P_detect = 0.10 + capital_gap + payout_ratio + leverage_modifier`

**Expected Value Calculation**:

```
eV = (profits_extracted_before_bankruptcy) 
     - P(veil_pierced) × (personal_liability + clawback_of_extracted_profits + fraud_charges)
     - P(detection_before_liability_event) × (forced_capitalization + estoppel)
```

**System Detection**:
1. **Insurer audit**: Insurer flags insufficient capital for risk level
2. **Creditor investigation**: After bankruptcy, creditor sues to pierce veil
3. **Pattern recognition**: Same beneficial owner with multiple bankrupt entities

**System Response**:
1. Under LS, graduated liability applies: insufficient capitalization can trigger veil piercing
2. Extracted profits clawed back from shareholders
3. Court can impose personal liability for willful under-capitalization
4. Repeat operators classified as "Systemic Sabotage"

### 12.2 Subsidiary Quarantine Exploitation

**Mechanic**: Agent uses otherwise-legitimate subsidiary quarantine to isolate profitable operations from liability-generating operations, letting the liability-bearing subsidiary go bankrupt while the profitable one continues.

**Prerequisites**:
- Corporate group with multiple subsidiaries
- Quarantine is legitimate (different management, separate accounts)
- Liability-generating operation is in a weakly-capitalized sub

**Detection Probability**:
- Low if quarantine is genuine (P_detect ≈ 0.15)
- Higher if capital or management is shared (+0.20)

**System Response**:
- If quarantine is genuine: legal, bankruptcy of liability sub is expected behavior
- If quarantine is fake: veil pierced, parent entity liable
- Insurers may refuse to cover subsidiaries with insufficient capital

### 12.3 Judgment-Proof Entity Structuring

**Mechanic**: Agent structures all assets to be held by entities that never engage in liability-generating activities, while operations are run by entities with no assets — "empty shell" operating model.

**Prerequisites**:
- Asset-holding entity (owns land, IP, equipment) — leases to operating entity
- Operating entity (conducts business, generates liability) — has no assets
- Lease payments drain operating entity of cash

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Operating entity asset ratio | +0.30 if assets < 5% of potential liability |
| Lease payment / revenue ratio | +0.25 if > 60% of revenue goes to asset entity |
| Same control group behind both entities | +0.20 |
| Insurer credit check | +0.15 |

**System Response**:
- "Single business enterprise" doctrine: entities treated as one for liability purposes
- Lease payments considered fraudulent conveyances if timed near liability events
- Personal liability for controlling persons

---

## 13. JUDGMENT EVASION / ASSET FLIGHT

### 13.1 Pre-Judgment Asset Movement

**Mechanic**: As soon as agent learns they will likely lose a lawsuit, they move assets beyond reach (offshore, crypto, family transfers) before the judgment is entered.

**Prerequisites**:
- Agent has advance notice of likely adverse judgment
- Assets are liquid or can be quickly liquidated
- Destination jurisdiction does not enforce LS judgments

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Timing (asset movement vs. case filing) | +0.35 if moved within 30 days of filing |
| Destination jurisdiction | -0.10 if non-cooperative, +0.15 if LS member |
| KYC/KYA Ledger compliance | -0.30 if ledger is properly maintained |
| Size of transfer | +0.10 per $1M equivalent |
| Use of privacy coins / mixers | -0.25 |

Base detection probability: `P_detect = 0.20 + timing_modifier + transfer_size - KYC_level - concealment_method`

**Expected Value Calculation**:

```
eV = (assets_moved - costs_of_moving) × P(evasion_success)
     - P(detection) × (judgment_enforcement + asset_clawback + fraud_on_court_penalties + repo_bounty)
     - (opportunity cost of assets in less-productive jurisdiction)
```

**System Detection**:
1. **Asset freeze injunction**: Court can freeze assets when lawsuit is filed (if plaintiff shows likelihood of flight).
2. **Financial monitoring**: Banks/insurers report large or suspicious transfers.
3. **Post-judgment investigation**: Creditor traces asset movements, can sue recipients for fraudulent conveyance.
4. **Repo-bounty**: Alliance issues Asset Recovery Bounty (200% of judgment value) to incentivize recovery.

**System Response**:
1. **Worldwide freezing order**: Court orders all known financial institutions to freeze assets.
2. **Fraudulent conveyance reversal**: Court claws back assets from transferees.
3. **Asset Recovery Bounty**: 200% of judgment value — PMCs and repo firms pursue globally.
4. **Contempt**: Non-compliance leads to escalating sanctions (asset liens, insurance revocation, guild expulsion).
5. **Ultimate sanction**: No one will do business with a judgment-evader — economic death.

### 13.2 Strategic Bankruptcy

**Mechanic**: Agent files for bankruptcy (corporate dissolution) when liability exceeds assets, discharging obligations and starting anew.

**Prerequisites**:
- Agent has operated through a limited-liability entity
- Entity has insufficient assets to cover liabilities
- Agent can move human capital (skills, relationships, IP) to a new entity

**Detection Probability**: 
- Legal if done properly (P_detect = 0 for legitimate bankruptcy)
- Fraudulent if assets were stripped before filing (+0.35)

**System Response** (LS-specific):
- LS limits the usefulness of strategic bankruptcy:
  - **Personal liability for executives** if under-capitalization was intentional
  - **Graduated liability** means the natural persons behind the entity may still be liable
  - **Reputation database** follows the principals to new ventures
  - **Insurer scrutiny** of new entity increases premiums (recidivism risk premium)

---

## 14. ACTUARIAL COMMONS MANIPULATION

### 14.1 Data Pollution

**Mechanic**: Agent submits false or misleading data to the Actuarial Commons to corrupt risk models, either to lower their own risk classification or to raise competitors'.

**Prerequisites**:
- Agent can submit data to Actuarial Commons
- Data verification is imperfect
- Agent's risk type is a significant fraction of the data pool

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Data point deviation from peer median | +0.25 per 2 standard deviations |
| Submission volume (agent's share of pool) | +0.10 per 5% of pool |
| Cross-validation with alternative data sources | +0.20 if available |
| Actuarial Commons data quality audit | +0.20 per audit cycle |

Base detection probability: `P_detect = 0.10 + data_deviation + share_of_pool + cross_validation`

**Expected Value Calculation**:

```
eV = expected_reduction_in_own_premiums × (1 - P_detect)
     - P_detect × (banned_from_AC_submission + fine + insurer_rate_penalty)
```

**System Detection**:
1. **Statistical outlier detection**: Actuarial Commons flags submissions that are statistical outliers relative to peer groups.
2. **Cross-validation**: AC cross-references submissions with Glass Box data, insurer audits, and alternative sources.
3. **Replication failure**: If other agents cannot replicate the claimed risk profile, investigation triggered.

**System Response**:
1. Data points removed from AC models
2. Agent banned from submitting data for specified period
3. Insurers may apply a "known manipulation" premium surcharge
4. Fine equal to manipulation benefit × 3

### 14.2 Model Arbitrage (Gaming Public Risk Models)

**Mechanic**: Agent reverse-engineers the public Actuarial Commons risk model and structures their behavior to score well (low risk) while actually maintaining high risk — effectively "teaching to the test."

**Prerequisites**:
- AC risk model is fully transparent (as mandated)
- Agent can observe every input variable
- Agent can modify behavior on observable dimensions without changing actual risk

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Observed behavior vs. actual outcome divergence | +0.20 per divergence |
| Model input manipulation detection | +0.15 per manipulated variable |
| Insurer alternative risk assessment | +0.25 if insurer develops supplemental model |

**Expected Value Calculation**:

```
eV = (premium_reduction × steps) × (1 - P_detect)
     - P(detection) × (back_premiums + model_gaming_penalty)
```

**System Response**:
- If detected: reclassification at true risk level, back premiums
- AC may update model to close the gaming loophole
- Insurers develop supplementary risk signals that are harder to game

---

## 15. AUDITOR / CERTIFIER CAPTURE

### 15.1 Trust Broker Bribery

**Mechanic**: Agent bribes a Trust Broker (certifier) to issue a favorable certification despite known risks or defects.

**Prerequisites**:
- Agent needs a certification to operate (guild seal, safety cert, product approval)
- Trust Broker has financial vulnerability (low revenue, high debt)

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Certification cost deviation from market | +0.25 if significantly above or below |
| Certifier revenue from single client | +0.30 if > 50% from one source |
| Post-certification failure rate | +0.30 if above industry average |
| Whistleblower | +0.40 if certifier employee reports |
| Bounty auditor investigation | +0.20 per competing certifier |

Base detection probability: `P_detect = 0.20 + fee_deviation + client_concentration + failure_rate + whistleblower`

**Expected Value Calculation**:

```
eV_certifier = (bribe) × (1 - P_detect)
               - P_detect × (liability_for_damages + professional_bond_forfeit + permanent_blacklist + personal_ruin)
```

Note: Under LS, certifiers are **personally liable** for harm caused by their negligence/bribery. The certifier's expected value is almost always negative — this strategy only works if the certifier is irrational or the bribe is extraordinarily high.

**System Detection**:
1. **Bounty auditing**: Competing certifier investigates and reports for reward (50% of target's liability bond).
2. **Post-disaster investigation**: If a certified facility fails, the certifier's certification process is scrutinized.
3. **Whistleblower protection**: Certifier employee reports bribery with statutory protection.
4. **Statistical analysis**: Pass rates, defect rates, and certification prices are published and analyzed.

**System Response**:
1. Certifier's Professional Liability Bond forfeited to victims
2. Certifier firm dissolved, principals permanently banned
3. All certifications issued by the captured certifier are voided
4. Facilities relying on those certifications must be re-certified

### 15.2 Auditor Rotation Evasion

**Mechanic**: Agent hires a new auditor each cycle to prevent any single auditor from gaining enough familiarity to detect problems — rotating before accountability can form.

**Prerequisites**:
- Agent is required to undergo periodic audits
- Multiple auditors compete for business

**Detection Probability**: Low (P_detect ≈ 0.10)
- Detected if consecutive auditors flag a "surface-level audit" concern

**System Response**:
- Actuarial Commons can mandate a minimum auditor engagement period
- Court can appoint a PCS for deep audit if pattern detected

---

## 16. DATA LEVIATHAN / SURVEILLANCE ABUSE

### 16.1 Surplus Data Collection (Scope Creep)

**Mechanic**: Insurer or trust broker collects more data than the constitutional minimum, using the "we might need it someday" rationale to build a surveillance database.

**Prerequisites**:
- Constitutional Knowledge Boundary (Glass Box Personal Mandate) is in effect but enforcement is weak
- Insurer can frame data collection as "necessary for underwriting"

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Data points collected vs. published minimum | +0.20 per category beyond minimum |
| Cross-line data aggregation | +0.30 if combining health + auto + property data |
| Citizen complaints to Actuarial Commons | +0.10 per complaint |
| ZKP auditor review | +0.20 per audit |

**System Response**:
1. Constitutional challenge: Citizen sues under Glass Box Personal Mandate
2. Court orders data minimization
3. Insurer license restricted or revoked for pattern of violations
4. Three-Source Mandate makes single-insurer surveillance less valuable (citizen has 2 other policies)

### 16.2 Behavioral Pricing Discrimination

**Mechanic**: Insurer uses unprotected behavioral proxies to price discriminate against protected classes (political affiliation, religion, lifestyle) under the guise of "actuarial accuracy."

**Prerequisites**:
- Insurer has data on protected characteristics (inferred or collected)
- Correlation exists between protected characteristic and risk
- Insight is statistically valid

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Pricing disparity across protected categories | +0.30 per category |
| Actuarial model reveals protected proxy variables | +0.25 if proxy variables included |
| Citizen complaint + investigation | +0.20 |

**System Response**:
- Court finds discrimination → mandatory coverage at standard rate
- Insurer fined, license reviewed
- Model variables published and audited

---

## 17. WHISTLEBLOWER SUPPRESSION

### 17.1 Retaliatory Litigation

**Mechanic**: Agent sues a whistleblower for defamation, breach of NDA, or tortious interference to intimidate them and deter others.

**Prerequisites**:
- Agent has engaged in wrongdoing
- Whistleblower has reported or is threatening to report
- LS whistleblower protections exist but must be invoked

**Detection Probability**: High (P_detect ≈ 0.35 if whistleblower countersues)

**Expected Value Calculation**:

```
eV = (deterrence_value × other_potential_whistleblowers)
     - P(whistleblower_wins) × (treble_damages + legal_costs + secondary_guild_liability)
     - reputation_damage_from_retaliation_revelation
```

**System Response**:
- Under LS: NDA void for fraud disclosure; retaliatory suit → treble damages for whistleblower
- Guild mutual bears secondary liability if it knew about suppression
- Court may issue anti-suit injunction

### 17.2 Blacklisting / Career Destruction

**Mechanic**: Agent coordinates with guilds and employers to ensure whistleblower cannot find work in their profession, using informal networks to communicate "this person is trouble."

**Prerequisites**:
- Whistleblower is in a profession with concentrated guild control
- Agent has influence in the guild or industry

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Whistleblower employment gap after reporting | +0.25 if significantly above base rate |
| Communication trail (email, guild network) | +0.20 if discovered |
| Multiple employers giving same reason | +0.15 if pattern is identical |

**System Response**:
- Court order against blacklisting
- Treble back pay + damages for career harm
- Guild mutual liable if it participated
- Individual participants personally liable

---

## 18. COURT CORRUPTION

### 18.1 Judicial Bribery

**Mechanic**: Agent bribes a judge or court administrator to obtain favorable rulings.

**Prerequisites**:
- Court has discretionary power in rulings
- Judge has financial or personal vulnerability
- Bribe can be concealed

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Ruling pattern deviation from precedent | +0.30 per case |
| Judge's lifestyle changes | +0.25 if sudden wealth appears |
| Litigant win rate at specific court | +0.25 if > 80% for one party type |
| Insider tip (court employee) | +0.35 |
| Bounty hunter investigation | +0.20 |

Base detection probability: `P_detect = 0.25 + ruling_deviation + win_rate + insider_flag`

**Expected Value Calculation**:

```
eV_briber = (favorable_ruling_value × cases) - bribe_cost
            - P_detect × (bribery_charges + judgment_reversal + reputation_damage)

eV_judge = bribe - P_detect × (personal_ruin + disbarment + asset_forfeiture + prison)
```

**System Detection**:
1. **Win rate statistics**: Actuarial Commons publishes court bias metrics. Courts with extreme party-type win rates are investigated.
2. **Insurer whitelist**: Insurers monitor court bias. Biased courts are removed from whitelists, losing business.
3. **Court-sues-court mechanism**: Competing court sues corrupt court for adjudicative negligence.
4. **Lifestyle audit**: Sortition oversight board can trigger judge asset review.
5. **Whistleblower bounty**: Court employees have financial incentive to report.

**System Response**:
1. Court's liability insurance becomes unaffordable → court cannot operate
2. Cases re-assigned to other courts; corrupt court's judgments vacated
3. Judge personally liable for damages caused by corrupt rulings
4. Permanent ban from judicial service
5. If corruption is systemic, court dissolved by market forces

### 18.2 Systematic Case Steering (Docket Manipulation)

**Mechanic**: Court administrator assigns high-value or politically sensitive cases to friendly judges, low-value cases to unfriendly judges.

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Case assignment uniformity | +0.25 if assignments deviate from random by > 20% |
| Judge-case outcome correlation | +0.20 per judge with > 80% win rate |
| Administrator relationship with parties | +0.15 if conflict of interest exists |

**System Response**:
- Mandatory random assignment audit
- Administrator fired and personally liable for damages from biased outcomes
- Court certification reviewed

---

## 19. PRIVATE CIVIL SERVANT (PCS) ABUSE

### 19.1 PCS Bribery / Collusion

**Mechanic**: Agent bribes a PCS during a deep audit to issue a false "verified clean" attestation, concealing violations.

**Prerequisites**:
- Agent's operations are under PCS warrant investigation
- At least one PCS on the audit team can be corrupted
- Other PCSs on the team must also be corrupted or neutralized

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| PCS bond-to-examination ratio | -0.20 per 10× bond multiple (higher bond = more to lose) |
| Number of PCSs on audit team | +0.15 per extra PCS (harder to corrupt all) |
| Surety monitoring frequency | +0.20 per surety check per period |
| PCS lifestyle change | +0.30 if sudden wealth appears |
| Whistleblower among sureties | +0.40 |

Base detection probability: `P_detect = 0.30 + PCS_count_bonus + surety_monitoring + lifestyle_change - bond_ratio`

The multi-PCS requirement (2-3 independent PCSs) makes this extremely difficult — all must be corrupted simultaneously without the others or their sureties noticing.

**Expected Value Calculation**:

```
eV_PCS = bribe - P_detect × (total_disgorgement + permanent_ban + surety_bond_forfeit + personal_ruin)

eV_briber = (harm_concealed - bribe) 
            - P_detect × (total_liability + obstruction_charges + systemic_sabotage_classification)
```

**System Response**:
1. PCS: Total disgorgement of all income from all sources for life
2. PCS: Surety bonds forfeited to victims
3. PCS: Permanent ban from PCS service
4. Briber: Full liability for concealed harm + obstruction of justice
5. Classified as "Systemic Sabotage" → maximum penalties

### 19.2 PCS Extortion

**Mechanic**: PCS threatens to issue a negative attestation (or leak proprietary data) unless the agent pays a bribe, weaponizing the deep-access privilege.

**Prerequisites**:
- PCS has access to agent's legitimate trade secrets
- Agent cannot afford public exposure of proprietary data (even if compliant)

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Surety monitoring of PCS communication | +0.20 if surety reviews PCS contacts |
| Pattern of "clean" attestations followed by demands | +0.25 |
| Agent reports extortion attempt | +0.50 |
| Independent PCS on same team flags anomaly | +0.30 |

**System Response**:
- PCS immediately stripped of status
- Total disgorgement + criminal extortion charges
- Surety bonds forfeited
- Agent's data sealed, PCS's attestation voided

---

## 20. SANDBOX ZONE LEAKAGE

### 20.1 Controlled Experiment Escape

**Mechanic**: Agent operates in a Sandbox Zone (limited liability restored) but allows harm to escape the zone — pollution leaking out, experimental pathogen released, drone crash outside perimeter.

**Prerequisites**:
- Agent operates within a designated Sandbox Zone
- Containment is imperfect (probability of escape)
- Strict liability snaps back on escape

**Detection Probability**: Automatic if harm has visible effects outside the zone. Probability depends on:

| Factor | Base modifier |
|--------|--------------|
| Immediate visibility of escape (smoke, debris, casualties) | +0.50 if immediately visible |
| Detection latency | -0.10 per day of delay |
| Monitoring infrastructure at perimeter | +0.20 per sensor type |

**Expected Value Calculation**:

```
eV = (innovation_gains_from_fast_operation × steps_before_escape) 
     - P(escape) × (strict_liability_damages + personal_ruin + loss_of_sandbox_privilege)
```

Under LS, containment failure means **immediate strict liability** — no cap, no insurance shield. This is designed to make the expected value negative for any rational actor.

**System Response**:
1. Strict liability for all harm caused outside the zone — unlimited
2. Personal liability for all executives and investors
3. Sandbox Zone privileges revoked permanently for the entity
4. Zone itself may be decommissioned if containment was inadequate

### 20.2 Sandbox as Regulatory Arbitrage

**Mechanic**: Agent conducts operations in a Sandbox Zone that should require insurance/external safety standards, then moves the product to the general market without the safety testing that would have been required outside.

**Prerequisites**:
- Sandbox Zone has relaxed safety/insurance requirements
- Product can be developed in zone and deployed outside
- "Graduated path" mechanism is weak or gamed

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Time from zone exit to market deployment | +0.30 if < 30 days |
| Gap between zone testing and real-world conditions | +0.25 if substantially different |
| Post-deployment incident rate | +0.20 per incident |

**System Response**:
- Full liability for any harm caused by insufficiently-tested product
- Sandbox Zone exit protocols tightened
- Agent may be barred from future sandbox access

---

## 21. PATENT / HARBERGER IP GAMING

### 21.1 Patent Trolling Through Harberger

**Mechanic**: Agent registers a broad, low-quality patent with a high Tier 1 value (to deter buyout) and a low Tier 2 licensing fee, then sues anyone using the technique for licensing fees.

**Prerequisites**:
- Agent has obtained a patent registration
- Patent scope is broad enough to cover common practices
- Agent has capital to pay Tier 1 tax and litigate

**Detection Probability**: Self-limiting — the Harberger mechanism makes trolling expensive:

| Factor | Effect |
|--------|--------|
| High Tier 1 value | Pays high annual tax (3% LVT on declared value) |
| Low licensing revenue | If no one licenses, generates no income |
| Buyout risk | At high Tier 1, buyout price deters purchase but tax is painful |

**Expected Value Calculation**:

```
eV = (licensing_revenue × licensees) 
     - (tier1_tax) 
     - (litigation_costs_of_enforcing_against_infringers)
     - P(buyout) × (loss_of_patent_at_Tier1_price)
```

The Harberger design makes trolling unprofitable for most patents — the tax burden on a high Tier 1 declaration exceeds revenue if no genuine licensees exist.

**System Response**:
- Market-based: Patent generates $0 if it has no actual users
- Tax burden forces holder to either commercialize or sell
- Rival can bid up Tier 1 price → holder pays more tax or sells

### 21.2 Hostile Patent Buyout

**Mechanic**: Rival bids up the Tier 1 price of a competitor's patent to raise their tax burden, forcing them to either sell (at the inflated price) or pay the higher tax.

**Prerequisites**:
- Target holds valuable patent
- Rival has capital to post 6-month Option Bond
- 14-day free window + 20% penalty applies

**Detection Probability**: Low (this is intended Harberger mechanism behavior)

**Expected Value Calculation**:

```
eV_bidder = - (opportunity_cost_of_bond_capital)
            + P(sale) × (patent_value - declared_price)
            + P(no_sale) × (20%_penalty_payment - bond_cost)
```

**System Response**:
- Market mechanism — not abuse by design (Option Premium is part of the system)
- If pattern is harassment (repeated bids on same patent without intention to buy), target can sue for tortious interference
- 14-day free window + 20% penalty for refusal already deters casual griefing

---

## 22. THREE-SOURCE MANDATE EVASION

### 22.1 Common Ownership of All Three Insurers

**Mechanic**: Agent nominally has three insurance policies, but all three are underwritten by entities under common ownership, defeating the anti-collusion purpose of the Three-Source Mandate.

**Prerequisites**:
- Agent (or their guild) controls multiple insurer entities
- Actuarial Commons does not verify independence of sources

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Ultimate beneficial ownership overlap | +0.35 if same entity owns >2 of 3 |
| Same reinsurance backing | +0.20 if all three use same reinsurer |
| Claims processing outsourced to same firm | +0.15 |
| Premium pricing correlation | +0.20 if near-identical pricing |

**System Response**:
- Mandate violation → must obtain genuinely independent third policy
- Fine equal to 1 year of premium for all three policies
- Flagged for potential collusion investigation

### 22.2 Single-Insurer Dependency in Practice

**Mechanic**: Agent maintains three policies on paper, but functionally relies on only one (low deductibles, high limits on primary; high deductibles, low limits on secondaries), defeating the "any one insurer can drop you" protection.

**Prerequisites**:
- Insurers allow differentiated policy terms
- Agent can meet the minimum legal requirements for all three while concentrating risk on one

**Detection Probability**: Low (P_detect ≈ 0.10) — this may be legal exploitation of policy structure

**System Response**:
- Actuarial Commons may set minimum coverage standards for each of the three policies
- If a dominant insurer drops the agent, the other two must actually provide adequate coverage — agent's risk increases

---

## 23. DIVIDEND FARMING / PARASITIC BEHAVIOR

### 23.1 Subsistence Floor Arbitrage

**Mechanic**: Agent lives entirely off the Citizen's Dividend in the cheapest compact, contributing nothing economically while consuming more in services than they pay in LVT.

**Prerequisites**:
- Dividend exceeds subsistence costs in cheapest compact
- Agent has no land holdings (pays no LVT)
- System allows indefinite non-participation

**Detection Probability**: None — this is an intended feature of the system (subsistence floor)

**Expected Value Calculation**:

```
eV = dividend_income - cost_of_living - lvt_paid(0) + wellbeing_loss_if_agent_has_purpose_preference
```

**System Response**:
- **No punitive response** — this is by design
- The moving-target cheapest-area mechanism encourages dispersion
- Agent may face higher insurance premiums if classified as "high risk" (unemployed)
- Guild membership and skill development are voluntary — no compulsion to work

### 23.2 Dividend Maximization Through Strategic Voting

**Mechanic**: Agent votes (via House of Repeal or compact referendum) to maximize short-term dividend at the expense of long-term sustainability: accelerate resource extraction, block pollution controls, oppose LVT adjustments.

**Prerequisites**:
- Agent is eligible to vote in HoR or compact referenda
- Dividend formula ties payout to current revenue minus costs
- Short-term revenue boost is visible; long-term costs are delayed

**Detection Probability**: None (voting is a right)

**Expected Value Calculation**:

```
eV = (short_term_dividend_increase × steps_before_negative_effects_manifest)
     - (long_term_liability_increases + dividend_reduction_when_costs_materialize)
     + (health_insurance_premium_increase_if_pollution_harms_health)
```

**System Response**:
- **Market-based correction**: LVT on extraction/concession land adjusts
- **Health-insurance feedback loop**: If voting causes pollution, health premiums rise more than dividend gains
- **Externality Vaults**: Revenue from high-impact extraction held in restoration escrow, not dividend pool
- **Constitutional caps**: Max 20% of dividend from non-LVT sources

---

## 24. COMPACT ARBITRAGE / REGULATORY SHOPPING

### 24.1 Optimal Compact Selection

**Mechanic**: Agent selects which compact to reside/operate in based on which compact's rules maximize their personal advantage — lowest LVT for landowners, highest court bias for plaintiffs, laxest environmental rules for polluters.

**Prerequisites**:
- Multiple compacts with differentiated rules
- Free movement of citizens and capital (constitutional)
- Agent has resources to migrate

**Detection Probability**: None — this is an intended feature of compact differentiation

**System Response**:
- **No punitive response** — the Exodus Equilibrium is by design
- Compacts compete for residents and businesses
- Migration flow data is public; compacts adjust their rules

### 24.2 Dual-Residence Exploitation

**Mechanic**: Agent claims residence in two compacts simultaneously to access benefits of both (voting rights, lower LVT on land in one, better court access in another).

**Prerequisites**:
- Loophole in compact residency definitions
- Agent can maintain presence in both compacts

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Tax residence inconsistency | +0.30 if LVT paid in different compact than voting |
| Time-spent records (if available) | +0.20 if split < 50/50 |
| Utility/banking address | +0.15 if multiple active addresses |

**System Response**:
- Agent must select primary residence for tax/voting purposes
- Back taxes owed for improper dual claims
- If fraudulent, penalties

---

## 25. FEEBATE / SIN TAX GAMING

### 25.1 Feebate Boundary Gaming

**Mechanic**: Agent restructures their behavior/holdings to barely meet the "good actor" threshold for a rebate while barely avoiding the "bad actor" threshold for a fee, maximizing net subsidy.

**Prerequisites**:
- Feebate system with defined thresholds (e.g., vehicle MPG tiers)
- Agent can precisely control the metric being measured
- Thresholds are static and predictable

**Detection Probability**: Low (P_detect ≈ 0.10) — this is intended behavioral response to incentives

**System Response**:
- Feebate thresholds can be recalibrated by the Actuarial Commons
- This is feature, not bug — agents responding to price signals
- If gaming is extreme, feebate formula adjusted to close loopholes

### 25.2 Sin Tax Avoidance (Substitution)

**Mechanic**: Agent substitutes a sin-taxed activity for an untaxed activity that produces the same harm (e.g., switching from taxed cigarettes to untaxed vaping with similar health effects, or switching from a taxed pollutant to an unregulated one).

**Prerequisites**:
- Sin tax covers a narrow definition of the harmful activity
- Substitute exists that produces similar externalities

**Detection Probability**: Low (P_detect ≈ 0.10) — substitution is hard to detect without health outcome monitoring

**System Response**:
- Actuarial Commons expands sin tax definition to cover substitutes
- Evolution Loop: if new substitute causes harm, liability attaches → insurance prices the risk

---

## 26. WAR BOND / EMERGENCY POWERS EXPLOITATION

### 26.1 False Flag for War Bounty

**Mechanic**: Strategist (or cartel) fabricates or exaggerates a foreign threat to trigger War Bond mechanism, issuing debt that enriches allies (PMC contractors, bond underwriters) while the broader population pays.

**Prerequisites**:
- Strategist can plausibly claim imminent foreign threat
- War Bond mechanism requires bond posting but oversight may be weak during crisis
- Bonded Executive emergency powers are in effect

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Post-war audit independence | +0.30 if court is independent |
| Pre-war intelligence quality | +0.25 if intelligence was thin/contradictory |
| Strategist's personal bond size | -0.20 if large bond (real skin in the game) |
| War contractor relationship | +0.25 if contractors are politically connected |

**Expected Value Calculation**:

```
eV_strategist = (benefits_from_war - personal_bond_at_risk) 
                - P(detection) × (bond_forfeiture + personal_liability + impeachment)
```

The LS design makes this risky: Strategist posts personal assets as bond, and post-war audit examines every decision. If abuse is found, bond is forfeited.

**System Response**:
1. Post-war audit by independent private courts
2. If abuse found: Strategist's bond forfeited to victims
3. Strategist personally liable for unauthorized spending
4. Impeachment/recall by House of Repeal

### 26.2 Emergency Powers Extension

**Mechanic**: Bonded Executive finds pretext to extend 90-day emergency period beyond constitutional limits, avoid returning to normal legal constraints.

**Prerequisites**:
- Emergency has been declared
- House of Repeal oversight is weak or intimidated
- Citizens accept continued emergency

**Detection Probability**:
- High if House of Repeal is functional (P_detect ≈ 0.40)
- Low if HoR is captured (P_detect ≈ 0.10)

**System Response**:
- House of Repeal can fire executive with simple majority
- Courts can declare emergency extension unconstitutional
- Executive Oversight Panel can veto extension (2/3 vote)
- After one renewal, extension requires supermajority

---

## 27. BOUNTY SYSTEM MANIPULATION

### 27.1 False Bounty Claim

**Mechanic**: Agent fabricates evidence of a violation to collect a whistleblower or bounty-auditor reward.

**Prerequisites**:
- Bounty system exists (whistleblower, audit, asset recovery)
- Agent can create plausible but false evidence
- Verification process is imperfect

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Bounty amount relative to normal | +0.20 if outsized |
| Evidence quality investigation | +0.25 if investigation finds inconsistencies |
| Claimant's history of bounty claims | +0.15 per prior claim |
| Timing (close to system stress events) | +0.10 |

**System Response**:
- False claimant liable for damages caused to accused party
- False claimant banned from future bounty participation
- Legal costs paid by false claimant (English Rule)

### 27.2 Bounty Hunter Collusion (Sting Operations)

**Mechanic**: Bounty hunter induces an agent to commit a violation (or sets up a trap) to collect the bounty.

**Prerequisites**:
- Bounty exists for specific violation type
- Bounty hunter can influence target's behavior
- Entrapment defense is weak

**Detection Probability**:
- Moderate (P_detect ≈ 0.20)
- Court examines whether the target would have committed the violation without inducement

**System Response**:
- If entrapment found: bounty denied, evidence suppressed
- False claim by bounty hunter → fraud charges
- Target still liable if violation was independently motivated

---

## 28. REHABILITATION CONTRACT ABUSE

### 28.1 Convict Labor Exploitation

**Mechanic**: Rehabilitation contractor takes on convicts primarily to extract cheap labor, providing minimal rehabilitation while maximizing contract profit.

**Prerequisites**:
- Contractor holds rehabilitation contract from court
- Rehabilitation quality is difficult to monitor (low information environment)
- Convict has limited ability to complain (asymmetric power)

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Recidivism rate of contractor's graduates | +0.30 if above industry average |
| Complaints from current/former convicts | +0.15 per complaint |
| Rehabilitation program quality audit | +0.20 per audit |
| Convict Ladder progression rate | +0.25 if most convicts stay at Default level |

**System Response**:
1. Contractor sued for abuse by victim or advocacy trust
2. Contract revoked, reassigned to competitor
3. Contractor's liability insurance cancelled
4. Principals personally liable for mistreatment

### 28.2 Level Ladder Gaming

**Mechanic**: Contractor keeps convicts at low rehabilitation levels longer than warranted to maximize state/insurance funding, since higher levels may have lower per-convict payments.

**Prerequisites**:
- Payment structure incentivizes keeping convicts at lower levels
- Convict's ability to appeal level assignment is limited

**Detection Probability**:
- Moderate (+0.20 per appeal from convict)

**System Response**:
- Independent review of level assignments if pattern detected
- Contract payment restructured to incentivize progression

---

## 29. AI / BENEFICIARY LIABILITY EVASION

### 29.1 Unincorporated Autonomous Agent

**Mechanic**: Agent deploys an autonomous AI system that operates through smart contracts and decentralized ownership, with no identifiable legal person responsible for its actions.

**Prerequisites**:
- AI system capable of autonomous contracting and operation
- Smart contract DAO structure with distributed ownership
- No single wallet/entity that funded or benefited from the AI

**Detection Probability**: Under LS, the Beneficiary Liability Principle applies:

| Factor | Effect on detection |
|--------|-------------------|
| Distribution of benefit | +0.05 per wallet that received returns from AI |
| Funding source tracing ability | -0.30 if funding is from privacy-preserving sources |
| AI's public presence (domain registration, social media) | +0.20 if traceable |

**Expected Value Calculation**:

```
eV_beneficiaries = (gains_from_AI_operations) × (1 - P(liability_assigned))
                   - P(liability_assigned) × (proportional_liability_based_on_funding_share)
```

**System Response**:
- Beneficiary Liability Principle: All wallets that received value from the AI are proportionally liable
- Liability is several (each pays their share of funding), not joint
- Court issues order freezing known wallets
- Blockchain analysis traces value flows

### 29.2 AI Deployer Shell Game

**Mechanic**: Deployer of an AI system creates a shell entity with no assets as the nominal "deployer," while the real developers and beneficiaries remain hidden behind layers of contracts.

**Prerequisites**:
- Nominal deployer entity has no assets
- Real economic beneficiaries are shielded by contract layers
- AI causes harm

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Entity capitalization | +0.30 if near-zero |
| Personnel overlap | +0.20 if shell shares directors/employees with beneficial entities |
| Contract chain tracing | +0.15 per layer that can be followed |
| Beneficial ownership registry | -0.30 if well-maintained |

**System Response**:
- Beneficiary Liability Principle: trace the money, find the beneficiaries
- Corporate veil piercing for the nominal deployer
- Personal liability for those who directed, funded, or benefited

---

## 30. HOUSE OF REPEAL / POLITICAL CAPTURE

### 30.1 Post-Sortition Bribery

**Mechanic**: After a citizen is selected for the House of Repeal by sortition, interested parties bribe them to vote a particular way on pending repeals.

**Prerequisites**:
- HoR member has been selected (identity eventually known)
- Member has financial vulnerability or low civic commitment
- Bribe can be disguised (future job offer, deferred payment)

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Anonymity protocol (The Cloister) | -0.40 if member is anonymous |
| Independence Pension size | -0.30 per $100K annual pension |
| Sudden wealth change after service | +0.35 |
| Loyalty investigation | +0.20 if triggered by suspicious voting pattern |

Base detection probability: `P_detect = 0.30 - anonymity_protection - pension_modifier + wealth_change + investigation`

**Expected Value Calculation**:

```
eV_member = bribe - P_detect × (pension_forfeiture + personal_asset_forfeiture + criminal_liability)

eV_briber = (value_of_repeal × expected_impact) - bribe_cost
            - P_detect × (bribery_charges + antitrust_penalties)
```

**System Detection**:
1. **The Cloister**: Anonymous deliberation (member identity hidden until term ends) eliminates advance targeting
2. **Multi-group redundancy**: Critical votes assigned to 3 independent anonymous groups. Discrepancy triggers audit.
3. **Independence Pension**: Lifetime stipend that is forfeited + all personal assets if bribery proven
4. **Citizen monitoring**: Dividend reduction from corrupt votes alerts the public

**System Response**:
1. Total forfeiture of Independence Pension and all personal assets
2. Bribery classified as "High Crime of Systemic Sabotage"
3. Repeal vote voided, re-voted with different panel selection
4. Briber permanently banned from Trust Ledger

### 30.2 Deliberate Expertise Asymmetry (Informational Capture)

**Mechanic**: Industry experts provide technically complex but biased information to the HoR, exploiting members' lack of domain expertise to shape repeal decisions.

**Prerequisites**:
- HoR members are generalists (by design)
- Industry has concentrated expertise
- Adversarial expert funding is inadequate

**Detection Probability**: Low (P_detect ≈ 0.15) — hard to prove bad intent vs. reasonable disagreement

**System Response**:
- **Structural mitigation**: State-funded Counter-Experts for every proposal
- **Sortition**: Random members aren't permanent targets; the "expert educator" relationship must be rebuilt each cycle
- If pattern detected, Actuarial Commons can flag "biased testimony" patterns

---

## 31. SUPREME TRUST ORACLE (STO) CAPTURE

### 31.1 Compact Collusion to Capture STO

**Mechanic**: Several large compacts collude to nominate/capture the STO's decision-making process, using STO enforcement powers against rival compacts.

**Prerequisites**:
- Multiple compacts can coordinate on STO appointments/funding
- STO has enforcement power (Trust Blockade, compact dissolution)
- Captured STO can target non-colluding compacts

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| STO decision pattern favoring colluding compacts | +0.30 per case |
| Compact voting bloc size | +0.20 if > 50% of compacts collude |
| STO personnel relationship with compact leadership | +0.20 if documented |

**System Response**:
- STO's enforcement actions subject to review by private courts
- Non-colluding compacts can secede from STO jurisdiction (compact exit)
- The 10-year Alliance sunset provides check on STO capture

---

## 32. FOREIGN INSURER EVASION

### 32.1 Unbonded Foreign Underwriting

**Mechanic**: Foreign insurer underwrites LS policies without posting the required surety bond or complying with Glass Box transparency rules.

**Prerequisites**:
- Foreign insurer operates in non-LS jurisdiction
- LS regulatory enforcement is imperfect
- LS customers accept lower-cost unregistered policies

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Premium price below market | +0.25 if > 30% below registered competitors |
| Insurance registration check | +0.30 if customers required to verify |
| Competitor report | +0.15 per registered insurer complaint |
| Claims payment failure | +0.40 (customers discover unregistered status when trying to claim) |

**System Response**:
1. **Primary**: Customers cannot operate legally without valid insurance from a registered provider — unregistered policies don't satisfy legal requirements
2. **Bond forfeiture**: No bond to forfeit, but the insurer is banned from ever operating in LS
3. **Customer consequences**: Customers operating on unregistered policies face personal liability for any harm (as if uninsured) — the risk is primarily on the customer, not the foreign insurer
4. **Market protection**: The Entry Bond requirement for foreign insurers (with Glass Box compliance) prevents this at scale

### 32.2 Treaty Shopping / Recognition Arbitrage

**Mechanic**: Agent obtains a liability insurance policy from a jurisdiction whose courts will not recognize LS judgments, intending to use the foreign court system to block subrogation.

**Prerequisites**:
- Foreign jurisdiction does not have reciprocity with LS
- Insurer in that jurisdiction is willing to write LS risks
- LS courts cannot easily enforce against that jurisdiction's assets

**Detection Probability**:
- High for LS authorities (P_detect ≈ 0.30)
- Insurance chain enforcement relies on subrogation — if foreign insurer covers LS risk, they become subject to LS jurisdiction for claims arising from that risk

**System Response**:
- LS treats foreign insurer as having consented to LS jurisdiction by underwriting LS risks
- Foreign insurer's assets within LS (if any) are reachable
- Foreign insurer's LS book of business can be impounded at border

---

## 33. COMPLEX / COMPOUND STRATEGIES

### 33.1 The Full Stack Exploit (Multi-Strategy Collusion)

**Mechanic**: A coordinated group of agents simultaneously executes multiple complementary strategies:
- Guild restricts membership (Artificially raises wages → increases business costs)
- Businesses pass costs to consumers via price-fixing cartel (Section 6)
- Insurers participate in premium collusion (Section 6.3)
- Courts are forum-shopped to friendly venues (Section 7)
- Land is under-declared via Harberger gaming (Section 3)
- Pollution is externalized (Section 9)
- Glass Box data is concealed (Section 10)

**Prerequisites**:
- Highly organized collusion across multiple sectors
- Long time horizon for benefits
- Sophisticated concealment across all fronts
- Trust or smart contracts among colluders

**Detection Probability**: Low per individual strategy (P_detect ≈ 0.10 each), but the combined detection risk compounds:

```
P(total_detection) = 1 - Π(1 - P_detect_i) for all strategies i
```

With 7 simultaneous strategies at P_detect ≈ 0.10 each:
`P(total_detection) = 1 - 0.9^7 = 1 - 0.478 = 0.522`

The more strategies used, the higher the overall detection probability. This is the system's natural defense against compound exploitation.

**Expected Value Calculation**: Compound of all strategy E&V, with:
- Synergy multiplier on returns (1.2-2.0× for interacting strategies)
- Compound detection probability
- Compound penalty (each detection triggers cascading exposure)

**System Response**:
1. Detection of any single strategy triggers investigation into others (discovery cascade)
2. "Systemic Sabotage" classification → maximum penalties across all fronts
3. All colluders permanently de-listed from Trust Ledger
4. Total asset forfeiture and personal liability for all participants

### 33.2 The Judgment-Proof Cascade

**Mechanic**: Agent A borrows from Agent B through Entity X (thinly capitalized). Agent A defaults. Entity X bankrupts. Agent B cannot collect. Agent A and Entity X's beneficial owners keep the profit, having pre-distributed all assets.

**Prerequisites**:
- Entity X has no meaningful assets
- Agent A has no meaningful assets beyond Entity X
- Beneficial owners have extracted all value before default

**Detection Probability**:
- High after bankruptcy filing (P_detect ≈ 0.30)
- Bankruptcy trustee traces asset flows

**System Response**:
- Tracing of beneficial ownership
- Clawback of pre-bankruptcy distributions to shareholders (fraudulent conveyance)
- Personal liability for directors who authorized distributions while insolvent
- Insurer may be liable for D&O coverage

### 33.3 The Reciprocal Insurance Shell Game

**Mechanic**: Two businesses each buy insurance from the other's captive insurer at inflated premiums. Both claim the premium as a business expense (reducing taxable income). Both insurers accumulate reserves that are effectively the business owners' own money. When claims are made, the captive pays out — but the captive was never a real risk pool.

**Prerequisites**:
- Two or more businesses with owner-controlled insurers (captives)
- Ability to set premiums at non-market rates
- No independent actuarial review of captive pricing

**Detection Probability**:

| Factor | Base modifier |
|--------|--------------|
| Premium-to-market ratio | +0.25 if > 50% above market |
| Claims ratio (paid claims / premiums) | +0.20 if < 20% |
| Captive insurer capital source | +0.20 if funded by same business owners |
| Actuarial Commons review | +0.20 per review cycle |

**System Response**:
- Tax deduction disallowed for excess premium
- Captive insurance arrangement voided if deemed non-arm's-length
- Permitted if captive is genuine risk-bearing entity (owns independent reserves)
- LS requires Glass Box for all insurers — captive arrangements are transparent

---

## 34. SYSTEM-LEVEL EXPLOITATION PATTERNS

### 34.1 Harberger LVT Collapse Tipping Point

**Description**: If enough land is simultaneously under-declared (Section 3.1) or a coordinated devaluation (Section 3.4) occurs, the LVT revenue base collapses below the level needed to fund the Citizen's Dividend and Alliance functions.

**Detection Probability**:

| Metric | Threshold |
|--------|-----------|
| LVT collected vs. budgeted | < 80% triggers automatic review |
| Land Value Index drop | > 20% in single period |
| Number of under-declared properties | > 30% of all properties |

**System Response**:
1. Automatic circuit breaker: LVT assessed at prior-period values (emergency constitutional provision)
2. Actuarial Commons investigation of all affected properties
3. Harberger forced-sale mechanisms accelerated for under-declared properties
4. Interim borrowing against LVT futures to maintain dividend

### 34.2 Insurance Death Spiral Trigger

**Description**: Adverse selection, correlated risk, or deliberate gaming causes insurance premiums to rise, causing lower-risk members to drop coverage, causing premiums to rise further, causing collapse.

**Detection Probability**: Monitored by insurance pool solvency ratio

| Threshold | Action |
|-----------|--------|
| Solvency ratio < 100% | Watch mode |
| Solvency ratio < 80% | Market failure event triggered |
| Solvency ratio < 50% | Emergency Alliance backstop |

**System Response**:
1. Public Option insurance activated (assigned risk pool at 300% cap)
2. Three-Source Mandate prevents complete coverage loss
3. Guild Mutuals absorb members at cost
4. Reinsurance market stabilizes pools

### 34.3 Court Gridlock Cascade

**Description**: Flooding (Section 4) combined with complex litigation overwhelms court capacity, creating backlogs that delay legitimate cases, eroding trust in the system.

**Detection Probability**:

| Metric | Threshold |
|--------|-----------|
| Average case resolution time | > 3× standard deviation from mean |
| Pending cases / judge ratio | > 200:1 |
| Case filing rate acceleration | > 20% per period for 3 periods |

**System Response**:
1. Market: New courts enter the market (low barriers to entry)
2. Prices rise: Filing fees increase, reducing frivolous filings
3. Merit sorting: Courts prioritize high-value cases
4. Arbitration: Parties shift to faster arbitration clauses

---

## Summary: Strategy Risk Matrix

| # | Strategy | Detection Difficulty | Max Damage | Typical Penalty | Systemic Risk |
|---|----------|---------------------|------------|-----------------|--------------|
| 1.1 | Risk under-reporting | Medium | Medium | Back premiums + 2× | Low |
| 1.2 | Selective omission | Low-Medium | Medium | Policy cancellation | Low |
| 2.1 | Fabricated claim | Medium-High | Medium | Claim denied + fraud | Low |
| 2.2 | Claim inflation | Medium | Low | Adjusted payout | Low |
| 2.3 | Double-dipping | Medium | Low-Medium | All claims denied | Low |
| 3.1 | Land under-declaration | Self-enforcing | Variable | Property loss | Medium |
| 3.2 | Collusive under-declaration | Medium | High | Back taxes + penalties | High |
| 3.3 | Option Premium griefing | Self-limiting | Low | Griefer loses money | Low |
| 3.4 | Coordinated devaluation | High | Critical | Asset forfeiture | **Critical** |
| 4.1 | Frivolous mass litigation | Medium | Medium | Counter-suit costs | Medium |
| 4.2 | Discovery abuse | Low-Medium | Medium | Cost shifting | Low |
| 4.3 | Case recycling | Medium | Low | Preclusion order | Low |
| 5.1 | Closed shop | Medium | Medium-High | Antitrust penalties | Medium |
| 5.2 | Fee extraction | Medium | Medium | Charter review | Low |
| 5.3 | Cheap certification | Medium | Medium | Liability increase | Medium |
| 6.1 | Price-fixing | Medium-High | High | Treble damages + forfeiture | High |
| 6.2 | Bid-rigging | Medium | High | Contract void + penalties | High |
| 6.3 | Premium collusion | Medium | High | Market share caps | High |
| 7.1 | Court bias exploitation | Medium | Medium | Court reputation loss | Low |
| 7.2 | Cross-compact arbitrage | Low | Low | First-filed rule | Low |
| 8.1 | Efficient breach | Automatic | Low-Medium | Expectation damages | Low |
| 8.2 | Strategic default | Medium | High | Veil piercing | Medium |
| 8.3 | NDA enforcement abuse | Low | Medium | Treble damages | Medium |
| 9.1 | Direct pollution | Medium | High | Cleanup + damages | Medium-High |
| 9.2 | Cross-border pollution | Low-Medium | High | Inter-compact dispute | High |
| 9.3 | Long-latency dumping | Very Low | Critical | Future liability (PV) | **Critical** |
| 10.1 | Data concealment | Medium | Critical | Operation ban + forfeiture | **Critical** |
| 10.2 | Asset invisibility | Medium-High | Critical | Total personal liability | **Critical** |
| 10.3 | Model concealment | Medium | High | License revoked | High |
| 11.1 | Strategic fragmentation | Medium | Medium | Consolidation + back taxes | Medium |
| 11.2 | Vacancy evasion | Medium | Low-Medium | Triple LRT + penalties | Low |
| 11.3 | Compact LVT arbitrage | None (legal) | Low | None | Low |
| 11.4 | Land-use misclassification | Medium | Medium | Reclassification + penalties | Low |
| 12.1 | Insufficient capitalization | Medium | High | Veil piercing | Medium |
| 12.2 | Subsidiary quarantine | Low | Medium | Bankruptcy of sub | Low |
| 12.3 | Judgment-proof structuring | Medium | High | Single enterprise doctrine | High |
| 13.1 | Pre-judgment asset flight | Medium | Critical | Clawback + repo bounty | **Critical** |
| 13.2 | Strategic bankruptcy | Low | Medium | Personal liability | Medium |
| 14.1 | Data pollution | Medium | Medium | Banned from AC | Medium |
| 14.2 | Model arbitrage | Medium | Medium | Reclassification | Low |
| 15.1 | Certifier bribery | Medium | Critical | Bond forfeiture + ban | **Critical** |
| 15.2 | Auditor rotation | Low | Low | Mandated engagement | Low |
| 16.1 | Surplus data collection | Low-Medium | Medium | Data minimization order | Medium |
| 16.2 | Behavioral discrimination | Medium | High | Coverage + fines | Medium |
| 17.1 | Retaliatory litigation | High | Medium | Treble damages | Low |
| 17.2 | Blacklisting | Medium | High | Treble damages | Medium |
| 18.1 | Judicial bribery | Medium | Critical | Court dissolution | **Critical** |
| 18.2 | Docket manipulation | Medium | Medium | Mandatory random assignment | Medium |
| 19.1 | PCS bribery | High | Critical | Total disgorgement | **Critical** |
| 19.2 | PCS extortion | Medium | High | Criminal charges | High |
| 20.1 | Sandbox zone escape | High (visible) | Critical | Unlimited personal liability | **Critical** |
| 20.2 | Sandbox regulatory arbitrage | Medium | Medium | Full liability | Medium |
| 21.1 | Patent trolling | Self-limiting | Low | Tax burden > revenue | Low |
| 21.2 | Hostile patent buyout | Low | Medium | Torts claim for harassment | Low |
| 22.1 | Common ownership of insurers | Medium | Medium | Fine + re-compliance | Medium |
| 22.2 | Single-insurer dependency | Low | Low | Risk concentration | Low |
| 23.1 | Subsistence floor arbitrage | None (legal) | Low | None | Low |
| 23.2 | Dividend-max voting | None (legal) | Medium | Market correction | Medium |
| 24.1 | Compact selection | None (legal) | None | None | Low |
| 24.2 | Dual-residence exploitation | Medium | Low-Medium | Back taxes | Low |
| 25.1 | Feebate boundary gaming | Low | Low | Threshold recalibration | Low |
| 25.2 | Sin tax substitution | Low | Medium | Definition expansion | Low |
| 26.1 | False war flag | High | Critical | Bond forfeiture + liability | **Critical** |
| 26.2 | Emergency extension | Medium | Critical | Impeachment | **Critical** |
| 27.1 | False bounty claim | Medium | Medium | Fraud charges + ban | Low |
| 27.2 | Bounty entrapment | Medium | Low | Bounty denied | Low |
| 28.1 | Convict labor exploitation | Medium | Medium | Contract revoked | Medium |
| 28.2 | Level ladder gaming | Medium | Low | Independent review | Low |
| 29.1 | Unincorporated AI | Medium | High | Beneficiary liability | High |
| 29.2 | AI deployer shell game | Medium | High | Veil piercing | High |
| 30.1 | Post-sortition bribery | Medium-High | Critical | Total forfeiture | **Critical** |
| 30.2 | Informational capture | Low | High | Counter-expert mandate | High |
| 31.1 | STO capture | Medium | Critical | Compact secession | **Critical** |
| 32.1 | Unbonded foreign underwriting | Medium | Low-Medium | LS operation ban | Low |
| 32.2 | Treaty shopping | Medium | Medium | Jurisdictional reach | Medium |
| 33.1 | Full stack exploit | Medium-High | Critical | Total forfeiture | **Critical** |
| 33.2 | Judgment-proof cascade | Medium | High | Clawback | High |
| 33.3 | Reciprocal insurance shell | Medium | Medium | Void arrangement | Medium |
| 34.1 | LVT collapse | Medium | Critical | Emergency assessment | **Critical** |
| 34.2 | Insurance death spiral | Medium | Critical | Public option + mutuals | **Critical** |
| 34.3 | Court gridlock | Medium | High | Market entry + fee rise | Medium |

---

## Implementation Notes

### Strategy Controller Integration

The strategies in this library are loaded by the Strategy Controller (`simulation/src/adversarial/controller.py`) which evaluates each agent's situation each step. Strategies are parameterized:

```python
class AdversarialStrategy:
    name: str
    prerequisites: Callable[[Agent], bool]
    expected_value: Callable[[Agent, Environment], float]
    detection_probability: Callable[[Agent, Environment], float]
    response: Callable[[Agent, Court, Environment], None]
    concealment_options: list[str]  # What the agent can do to hide
```

### Detection Probability Computation

Each strategy's detection probability is computed from:
1. **Base rate** (the inherent detectability of the violation type)
2. **Agent modifiers** (concealment investment, sophistication, prior record)
3. **System modifiers** (audit frequency, transparency level, monitoring infrastructure)
4. **Discovery cascade** (detection of one violation may increase P_detect for related violations)

### Penalty Computation

Penalties follow LS design principles:
- **Market penalties** (premium increases, reputation loss, higher interest rates)
- **Legal penalties** (damages, legal costs under English Rule)
- **Structural penalties** (veil piercing, Glass Box revocation, operation ban)
- **Criminal penalties** (Systemic Sabotage classification, asset forfeiture)

The simulation computes all penalties using the mechanics defined in the LS rule implementations, not via abstract multipliers.

---

*This library is the single source of truth for adversarial agent behavior in the liability State simulation. Updated as new exploit vectors are discovered during simulation runs.*
