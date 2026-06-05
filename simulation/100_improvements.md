# Liability State Simulator — 100 Improvements with Codebase Cross-Reference

*Tagged: NEW (not in codebase), SPEC (designed but not built), PARTIAL (exists but incomplete)*
*Source = existing file where concept is documented. Dep = what must be built first.*

| # | Cat | Status | Improvement | Rationale | Source | Dep | Cost |
|---|-----|--------|-------------|----------|--------|-----|------|

| 1 | Labor | 🆕 NEW | **Wage competition - firms bid for scarce workers** | Enables monopolization/banking to propagate to wages |  | None | Medium |
| 2 | Labor | 📋 SPEC | **Occupational choice - agents select sector each step** | AGENT_MODEL.md design spec for job switching | AGENT_MODEL.md | Wage competition | Medium |
| 3 | Labor | 🆕 NEW | **Skill accumulation - human capital grows with experience** | Endogenous growth; tests LS vs US skill investment |  | Occupational choice | High |
| 4 | Labor | 🆕 NEW | **Minimum wage policy - compact-level wage floor** | Tests LS labor market with regulation |  | Compact governance | Low |
| 5 | Labor | ⚠️ PARTIAL | **Union bargaining - guild negotiates contractor wages** | agents/guild.py exists but has no wage negotiation | agents/guild.py | Guild module | Medium |
| 6 | Labor | 📋 SPEC | **Unemployment/job search - matching with duration** | AGENT_MODEL.md section 2.4 design, not coded | AGENT_MODEL.md | Occupational choice | Medium |
| 7 | Labor | 🆕 NEW | **Gig/contract work - multiple income streams per agent** | Modern labor reality the LS must handle |  | None | High |
| 8 | Labor | ⚠️ PARTIAL | **Pension/retirement accounts - guild or private savings** | Phase 4 has retirees but no savings mechanic | Phase 4 | Retiree module | Medium |
| 9 | Labor | 🆕 NEW | **Labor mobility costs - switching costs money/time** | Tests if mobility costs create de facto serfdom |  | Compact competition | Low |
| 10 | Labor | ⚠️ PARTIAL | **Occupational licensing - guild certification standards** | GuildRentSeeking strategy exists in adversarial | adversarial/controller.py | Guild module | Low |
| 11 | Finance | 🆕 NEW | **Fractional-reserve banking - banks create credit** | Enables credit cycles; tests LS stability vs runs |  | None | High |
| 12 | Finance | 📋 SPEC | **Central bank/lender of last resort** | MECHANICS_INVENTORY.md conceptual design | MECHANICS_INVENTORY.md | Banking | High |
| 13 | Finance | 🆕 NEW | **Competing currencies - compacts issue money** | Optimal currency area test for LS |  | Banking | Very High |
| 14 | Finance | 🆕 NEW | **Land-backed currency - 100% reserve by land registry** | Georgist monetary theory; comparison vs fiat |  | Harberger + banking | High |
| 15 | Finance | 🆕 NEW | **Bond market - govt/corp debt securities** | Fiscal policy analysis; LS borrowing capacity |  | Banking | High |
| 16 | Finance | 🆕 NEW | **Equity market - corporate shares to households** | Tests if unlimited liability suppresses equity |  | Business agent | Very High |
| 17 | Finance | 📋 SPEC | **Insurance-linked securities - cat bonds, reinsurance** | MECHANICS_INVENTORY.md section 6 design | MECHANICS_INVENTORY.md | Insurance | High |
| 18 | Finance | 🆕 NEW | **Peer-to-peer lending - uncollateralized credit** | Financial inclusion differences across systems |  | None | Medium |
| 19 | Finance | 🆕 NEW | **Smart contracts/DeFi - programmable money** | Tests LS legal system compatibility with crypto |  | None | Very High |
| 20 | Finance | 📋 SPEC | **Financial regulation - capital/leverage requirements** | ENFORCEMENT_MODEL.md section 3, not coded | ENFORCEMENT_MODEL.md | Banking | High |
| 21 | Land | ⚠️ PARTIAL | **Harberger self-assessment with forced-sale** | mechanics/harberger.py EXISTS but never wired! | mechanics/harberger.py | None | High |
| 22 | Land | 🆕 NEW | **Rental housing market - landlords lease to tenants** | Realistic housing; tests LVT pass-through to rents |  | Harberger market | Medium |
| 23 | Land | 🆕 NEW | **Mortgage market - land-secured home loans** | Interaction of LVT and credit; core housing dynamic |  | Harberger + banking | High |
| 24 | Land | 🆕 NEW | **Zoning/land-use regulation - compact density rules** | Tests if liability approach to nuisance handles zoning |  | Compact module | Medium |
| 25 | Land | 🆕 NEW | **Agricultural land - separate LVT rate for farmland** | Addresses farmer-critique from 10-pass debate |  | None | Low |
| 26 | Land | 📋 SPEC | **Property improvement - buildings separate from land** | MECHANICS_INVENTORY.md section 4 improvement value | MECHANICS_INVENTORY.md | Harberger market | High |
| 27 | Land | 🆕 NEW | **Gentrification - rising values displace residents** | Real-world LS critique; tests Dividend compensation |  | Rental + migration | High |
| 28 | Land | 🆕 NEW | **Eminent domain - compact condemnation for projects** | LS property rights framework stress test |  | Compact governance | Medium |
| 29 | Land | 🆕 NEW | **Foreign land ownership - non-citizen, no Dividend** | Real-world issue; tests stability under foreign purchase |  | None | Low |
| 30 | Land | 🆕 NEW | **Community land trusts - collective ownership, leases** | Alternative to private; tests LS with communal land |  | None | Medium |
| 31 | Govern | 📋 SPEC | **Compact-level voting - choose LVT rate, Dividend, budget** | ARCHITECTURE.md Compact Differentiation section | ARCHITECTURE.md | Compact module | High |
| 32 | Govern | 📋 SPEC | **Lobbying/regulatory capture - influence policy with $** | ENFORCEMENT_MODEL.md Capture section, not coded | ENFORCEMENT_MODEL.md | Governance module | High |
| 33 | Govern | ⚠️ PARTIAL | **Strategic tax competition - compacts optimize rates** | Dual_Compact in Phase 3 has fixed rates, not strategic | Phase 3 | Compact governance | Medium |
| 34 | Govern | 📋 SPEC | **Compact secession crisis - exit triggers trust blockade** | ARCHITECTURE.md Force Prohibition section | ARCHITECTURE.md | Compact governance | Very High |
| 35 | Govern | 📋 SPEC | **Constitutional amendment - supermajority rule changes** | ARCHITECTURE.md Supreme Trust Oracle section | ARCHITECTURE.md | Governance module | Low |
| 36 | Govern | 🆕 NEW | **Judicial selection - election vs sortition vs appointment** | Tests if court selection affects case quality |  | Court module | Medium |
| 37 | Govern | 🆕 NEW | **Bureaucratic agency competition - budget-maximizing** | Realistic public-sector dynamics currently missing |  | Governance module | High |
| 38 | Govern | 🆕 NEW | **Direct democracy referenda - citizens vote on policy** | Alternative to representative governance |  | Governance module | Medium |
| 39 | Govern | 🆕 NEW | **Partisan coalition formation - interest groups compete** | High-fidelity political economy modeling |  | Governance module | Very High |
| 40 | Govern | 📋 SPEC | **Whistleblower/bounty system - report violations for reward** | ARCHITECTURE.md adversarial audit bounties, not coded | ARCHITECTURE.md | Enforcement module | Medium |
| 41 | Demo | ⚠️ PARTIAL | **Full overlapping generations - birth, aging, death** | Phase 4 has 15 static retirees, not full OLG | Phase 4 | None | High |
| 42 | Demo | 🆕 NEW | **Endogenous fertility - births respond to Dividend** | Tests if Dividend is pronatalist or anti-natalist |  | Full OLG | Very High |
| 43 | Demo | 📋 SPEC | **Inter-compact migration - choose compact by policy** | ARCHITECTURE.md Compact Differentiation Exit section | ARCHITECTURE.md | Compact module | Medium |
| 44 | Demo | 📋 SPEC | **International migration - leave/enter LS entirely** | EVENT_MODEL.md Population Shock event | EVENT_MODEL.md | Compact module | High |
| 45 | Demo | 🆕 NEW | **Household formation - agents form family units** | Realistic consumption; economies of scale in housing |  | None | High |
| 46 | Demo | 🆕 NEW | **Education investment - public/private/guild schools** | Tests LS education quality vs state-run systems |  | Skill accumulation | High |
| 47 | Demo | ⚠️ PARTIAL | **Health insurance - separate risk pool for medical** | InsuranceMarket exists but covers all risks together | Insurance module | Insurance module | Very High |
| 48 | Demo | 📋 SPEC | **Disability/long-term care - permanent non-earners** | AGENT_MODEL.md mentions disability probability | AGENT_MODEL.md | Retiree module | Medium |
| 49 | Demo | 🆕 NEW | **Intergenerational wealth tracking - dynastic persistence** | Tests if LS enables mobility or creates dynastic wealth |  | Inheritance mechanic | Low |
| 50 | Demo | 📋 SPEC | **Criminal liability - tort-based crime resolution** | ARCHITECTURE.md crime via private tort framework | ARCHITECTURE.md | Court module | Very High |
| 51 | Enviro | 📋 SPEC | **Pollution tort - firms pay for damage via courts** | ARCHITECTURE.md Environmental harm definition | ARCHITECTURE.md | Court module | Medium |
| 52 | Enviro | 🆕 NEW | **Carbon pricing - tax or cap-and-trade** | Compares carbon pricing across all 10 systems |  | Tax module | Medium |
| 53 | Enviro | 📋 SPEC | **Natural resource commons - depletion with property rights** | ARCHITECTURE.md Commons Stewardship section | ARCHITECTURE.md | None | High |
| 54 | Enviro | 🆕 NEW | **Climate change - gradual warming, extreme weather** | Long-horizon stress test for insurance markets |  | Event system | Very High |
| 55 | Enviro | 🆕 NEW | **Renewable energy investment - green tech adoption** | Tests if LS accelerates or delays green transition |  | Business agent | High |
| 56 | Enviro | 🆕 NEW | **Waste/circular economy - recycling, disposal costs** | Growing real-world economic concern |  | None | Medium |
| 57 | Enviro | 🆕 NEW | **Biodiversity valuation - ecosystem service pricing** | Frontier topic; tests LS property rights framework |  | None | Very High |
| 58 | Enviro | 📋 SPEC | **Water rights/fisheries - common pool without authority** | ARCHITECTURE.md Aquifer extraction, Fisheries | ARCHITECTURE.md | Court module | High |
| 59 | Enviro | 📋 SPEC | **Nuisance liability - noise, light, odor as torts** | EVENT_MODEL.md mentions nuisance liability | EVENT_MODEL.md | Court module | Low |
| 60 | Enviro | 📋 SPEC | **Pandemic - contagious illness with public externalities** | EVENT_MODEL.md Pandemic shock, not coded | EVENT_MODEL.md | Event system | Very High |
| 61 | Tech | 🆕 NEW | **Endogenous R&D - firms invest in stochastic innovation** | Tests if LS framework encourages or discourages R&D |  | Business agent | High |
| 62 | Tech | 📋 SPEC | **Harberger patents - IP self-assessed, buyable** | Future_Ideas doc mentions Harberger patent framework | Future_Ideas | Harberger market | Medium |
| 63 | Tech | 📋 SPEC | **Automation/AI displacement - tech eliminates jobs** | EVENT_MODEL.md Technology Disruption shock, not coded | EVENT_MODEL.md | Event system | High |
| 64 | Tech | 🆕 NEW | **Knowledge spillovers - one firms R&D benefits others** | Core endogenous growth mechanism |  | Endogenous R&D | High |
| 65 | Tech | 🆕 NEW | **Network effects - value grows with user base** | Enables natural monopoly; LS antitrust via liability |  | Monopolization module | High |
| 66 | Tech | 🆕 NEW | **Platform economy - multi-sided digital markets** | Tests LS liability framework for platforms |  | Network effects | Very High |
| 67 | Tech | 🆕 NEW | **Data property rights - own and license personal data** | LS framework for privacy; property rights in data |  | None | High |
| 68 | Tech | 🆕 NEW | **Technology adoption lags - heterogeneous adoption rate** | Realistic productivity dispersion across firms |  | Business agent | Medium |
| 69 | Tech | 🆕 NEW | **Algorithmic collusion - AI price coordination** | Frontier antitrust; LS liability for tacit collusion |  | Monopoly + adversarial | Very High |
| 70 | Tech | 🆕 NEW | **Open-source commons - voluntary public good production** | Alternative to market-based production |  | None | Medium |
| 71 | Intl | 🆕 NEW | **Inter-compact trade - comparative advantage flows** | Tests if LS compacts trade more/less than US states |  | Compact + business | High |
| 72 | Intl | 🆕 NEW | **Tariffs/trade barriers - compact-level import taxes** | Tests if compact competition leads to protectionism |  | Inter-compact trade | Medium |
| 73 | Intl | 📋 SPEC | **War Escrow defense - PMC funding, invasion defense** | ARCHITECTURE.md Defense section, War Escrow NOT CODED | ARCHITECTURE.md | Compact + events | Very High |
| 74 | Intl | 🆕 NEW | **Foreign direct investment - external capital flows** | Crucial for international competitiveness analysis |  | Equity market | High |
| 75 | Intl | 📋 SPEC | **Treaty/alliance system - compacts form blocs** | ARCHITECTURE.md Alliance functions, not coded | ARCHITECTURE.md | Compact governance | Very High |
| 76 | Intl | 🆕 NEW | **Economic sanctions - compacts penalize each other** | Escalation dynamics within LS federation |  | Compact governance | Medium |
| 77 | Intl | 🆕 NEW | **Currency union - shared money across compacts** | Tests monetary stability without central bank |  | Banking | High |
| 78 | Intl | 📋 SPEC | **Refugee/asylum shock - external population inflow** | EVENT_MODEL.md Population Shock, incomplete | EVENT_MODEL.md | Event system | High |
| 79 | Intl | 📋 SPEC | **Inter-compact arbitration - dispute resolution** | ARCHITECTURE.md Supreme Trust Oracle, not coded | ARCHITECTURE.md | Court module | Medium |
| 80 | Intl | 🆕 NEW | **Development aid - richer compacts help poorer** | Tests if LS reduces inter-compact inequality |  | Compact governance | Low |
| 81 | Valid | 🆕 NEW | **Historical backtesting - US 1960-2020 vs real GDP/Gini** | THE single most critical missing validation step |  | Calibration module | High |
| 82 | Valid | 🆕 NEW | **Global sensitivity analysis - all parameters +-50%** | Identifies fragile vs robust findings |  | None | Medium |
| 83 | Valid | 🆕 NEW | **Monte Carlo uncertainty - distributions not point estimates** | Honest uncertainty quantification |  | Sensitivity analysis | Medium |
| 84 | Valid | 🆕 NEW | **Laffer curve validation - tax revenue peaks at realistic rate** | Minimal credibility test; currently completely untested |  | None | Low |
| 85 | Valid | 🆕 NEW | **Kuznets curve pattern - inequality over development** | Validates model inequality dynamics are realistic |  | None | Low |
| 86 | Valid | 🆕 NEW | **Phillips curve - inflation-unemployment tradeoff** | Validates model macro dynamics are realistic |  | Central bank module | Medium |
| 87 | Valid | 🆕 NEW | **External peer review - publish methodology for scrutiny** | Gold standard for scientific credibility |  | Documentation | Low |
| 88 | Valid | 🆕 NEW | **Comparative statics validation - match known elasticities** | Validates individual mechanism correctness |  | Calibration module | Medium |
| 89 | Valid | 🆕 NEW | **Out-of-sample testing - calibrate 60-90, test 90-2020** | Detects overfitting |  | Historical backtesting | Medium |
| 90 | Valid | ⚠️ PARTIAL | **Adversarial parameter testing - extreme values** | Phase 4 has min/max clamping, no formal adversarial test | Phase 4 | None | Low |
| 91 | Eng | 🆕 NEW | **YAML config files - replace opaque _mk() tuples** | Current system configs are fragile positional numbers | comparison_phase4.py | None | Low |
| 92 | Eng | 🆕 NEW | **Real-time web dashboard - live charts, parameter sliders** | Interactive exploration of parameter space |  | None | High |
| 93 | Eng | 🆕 NEW | **Jupyter notebook API - documented Python import** | Enables rapid prototyping of new dynamics |  | Docstring API | Medium |
| 94 | Eng | ⚠️ PARTIAL | **Regression test suite - 500+ tests across all mechanics** | Currently 21 tests in test_phase4_dynamics.py | test_phase4_dynamics.py | None | Medium |
| 95 | Eng | 🆕 NEW | **SQLite output database - structured cross-run querying** | Flat JSON limits analysis depth |  | None | Low |
| 96 | Eng | 🆕 NEW | **Multi-CPU parallel execution - multiprocessing seeds** | 50 sims in 3s good; 500+ would benefit |  | None | Low |
| 97 | Eng | 🆕 NEW | **Genetic parameter optimization - Pareto frontier search** | Discovers non-obvious optimal system designs |  | Sensitivity analysis | High |
| 98 | Eng | 🆕 NEW | **Complete API reference - all config keys, return schemas** | Current docstrings are minimal | comparison_phase4.py | None | Low |
| 99 | Eng | 🆕 NEW | **Docker container - pinned deps, one-command reproducibility** | Scientific reproducibility |  | None | Low |
| 100 | Eng | 🆕 NEW | **Property-based testing - invariant verification** | Catches bugs unit tests miss (money conservation) |  | None | High |

## Statistics
- **65** novel (not in codebase)
- **26** spec'd but not implemented
- **9** partially implemented
- Cost: Low=18, Medium=32, High=35, Very High=15

## Top Priority by Impact
1. **Harberger self-assessment (#21)** — LS core mechanism; mechanics/harberger.py EXISTS but never wired into comparison
2. **War Escrow defense (#73)** — Core LS institution; full spec in ARCHITECTURE.md but zero code
3. **Compact governance/voting (#31)** — Enables endogenous policy; unlocks 10+ dependent improvements
4. **Historical backtesting (#81)** — Without validation against real data, all rankings are provisional
5. **Fractional-reserve banking (#11)** — Credit cycles; tests LS stability claims vs traditional systems

## Quick Wins (Low Cost, No Dependencies)
#4, #9, #10, #25, #29, #35, #49, #59, #80, #84, #85, #87, #90, #91, #95, #96, #98, #99
