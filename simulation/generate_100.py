#!/usr/bin/env python3
"""Generate 100_improvements.md with codebase cross-references."""
cats = ['Labor','Finance','Land','Govern','Demo','Enviro','Tech','Intl','Valid','Eng']
cost_l = {'L':'Low','M':'Medium','H':'High','VH':'Very High'}
st = {'N':  'NEW','S': 'SPEC','P': 'PARTIAL'}
items = []
n = 0
def add(c, t, s, r, src, dep, co):
    global n; n += 1
    si = {'N': '🆕', 'S': '📋', 'P': '⚠️'}[s]
    items.append(f'| {n} | {cats[c-1]} | {si} {st[s]} | **{t}** | {r} | {src} | {dep} | {cost_l[co]} |')
# Labor Market
add(1,'Wage competition - firms bid for scarce workers','N','Enables monopolization/banking to propagate to wages','','None','M')
add(1,'Occupational choice - agents select sector each step','S','AGENT_MODEL.md design spec for job switching','AGENT_MODEL.md','Wage competition','M')
add(1,'Skill accumulation - human capital grows with experience','N','Endogenous growth; tests LS vs US skill investment','','Occupational choice','H')
add(1,'Minimum wage policy - compact-level wage floor','N','Tests LS labor market with regulation','','Compact governance','L')
add(1,'Union bargaining - guild negotiates contractor wages','P','agents/guild.py exists but has no wage negotiation','agents/guild.py','Guild module','M')
add(1,'Unemployment/job search - matching with duration','S','AGENT_MODEL.md section 2.4 design, not coded','AGENT_MODEL.md','Occupational choice','M')
add(1,'Gig/contract work - multiple income streams per agent','N','Modern labor reality the LS must handle','','None','H')
add(1,'Pension/retirement accounts - guild or private savings','P','Phase 4 has retirees but no savings mechanic','Phase 4','Retiree module','M')
add(1,'Labor mobility costs - switching costs money/time','N','Tests if mobility costs create de facto serfdom','','Compact competition','L')
add(1,'Occupational licensing - guild certification standards','P','GuildRentSeeking strategy exists in adversarial','adversarial/controller.py','Guild module','L')
# Financial
add(2,'Fractional-reserve banking - banks create credit','N','Enables credit cycles; tests LS stability vs runs','','None','H')
add(2,'Central bank/lender of last resort','S','MECHANICS_INVENTORY.md conceptual design','MECHANICS_INVENTORY.md','Banking','H')
add(2,'Competing currencies - compacts issue money','N','Optimal currency area test for LS','','Banking','VH')
add(2,'Land-backed currency - 100% reserve by land registry','N','Georgist monetary theory; comparison vs fiat','','Harberger + banking','H')
add(2,'Bond market - govt/corp debt securities','N','Fiscal policy analysis; LS borrowing capacity','','Banking','H')
add(2,'Equity market - corporate shares to households','N','Tests if unlimited liability suppresses equity','','Business agent','VH')
add(2,'Insurance-linked securities - cat bonds, reinsurance','S','MECHANICS_INVENTORY.md section 6 design','MECHANICS_INVENTORY.md','Insurance','H')
add(2,'Peer-to-peer lending - uncollateralized credit','N','Financial inclusion differences across systems','','None','M')
add(2,'Smart contracts/DeFi - programmable money','N','Tests LS legal system compatibility with crypto','','None','VH')
add(2,'Financial regulation - capital/leverage requirements','S','ENFORCEMENT_MODEL.md section 3, not coded','ENFORCEMENT_MODEL.md','Banking','H')
# Land
add(3,'Harberger self-assessment with forced-sale','P','mechanics/harberger.py EXISTS but never wired!','mechanics/harberger.py','None','H')
add(3,'Rental housing market - landlords lease to tenants','N','Realistic housing; tests LVT pass-through to rents','','Harberger market','M')
add(3,'Mortgage market - land-secured home loans','N','Interaction of LVT and credit; core housing dynamic','','Harberger + banking','H')
add(3,'Zoning/land-use regulation - compact density rules','N','Tests if liability approach to nuisance handles zoning','','Compact module','M')
add(3,'Agricultural land - separate LVT rate for farmland','N','Addresses farmer-critique from 10-pass debate','','None','L')
add(3,'Property improvement - buildings separate from land','S','MECHANICS_INVENTORY.md section 4 improvement value','MECHANICS_INVENTORY.md','Harberger market','H')
add(3,'Gentrification - rising values displace residents','N','Real-world LS critique; tests Dividend compensation','','Rental + migration','H')
add(3,'Eminent domain - compact condemnation for projects','N','LS property rights framework stress test','','Compact governance','M')
add(3,'Foreign land ownership - non-citizen, no Dividend','N','Real-world issue; tests stability under foreign purchase','','None','L')
add(3,'Community land trusts - collective ownership, leases','N','Alternative to private; tests LS with communal land','','None','M')
# Governance
add(4,'Compact-level voting - choose LVT rate, Dividend, budget','S','ARCHITECTURE.md Compact Differentiation section','ARCHITECTURE.md','Compact module','H')
add(4,'Lobbying/regulatory capture - influence policy with $','S','ENFORCEMENT_MODEL.md Capture section, not coded','ENFORCEMENT_MODEL.md','Governance module','H')
add(4,'Strategic tax competition - compacts optimize rates','P','Dual_Compact in Phase 3 has fixed rates, not strategic','Phase 3','Compact governance','M')
add(4,'Compact secession crisis - exit triggers trust blockade','S','ARCHITECTURE.md Force Prohibition section','ARCHITECTURE.md','Compact governance','VH')
add(4,'Constitutional amendment - supermajority rule changes','S','ARCHITECTURE.md Supreme Trust Oracle section','ARCHITECTURE.md','Governance module','L')
add(4,'Judicial selection - election vs sortition vs appointment','N','Tests if court selection affects case quality','','Court module','M')
add(4,'Bureaucratic agency competition - budget-maximizing','N','Realistic public-sector dynamics currently missing','','Governance module','H')
add(4,'Direct democracy referenda - citizens vote on policy','N','Alternative to representative governance','','Governance module','M')
add(4,'Partisan coalition formation - interest groups compete','N','High-fidelity political economy modeling','','Governance module','VH')
add(4,'Whistleblower/bounty system - report violations for reward','S','ARCHITECTURE.md adversarial audit bounties, not coded','ARCHITECTURE.md','Enforcement module','M')
# Demographics
add(5,'Full overlapping generations - birth, aging, death','P','Phase 4 has 15 static retirees, not full OLG','Phase 4','None','H')
add(5,'Endogenous fertility - births respond to Dividend','N','Tests if Dividend is pronatalist or anti-natalist','','Full OLG','VH')
add(5,'Inter-compact migration - choose compact by policy','S','ARCHITECTURE.md Compact Differentiation Exit section','ARCHITECTURE.md','Compact module','M')
add(5,'International migration - leave/enter LS entirely','S','EVENT_MODEL.md Population Shock event','EVENT_MODEL.md','Compact module','H')
add(5,'Household formation - agents form family units','N','Realistic consumption; economies of scale in housing','','None','H')
add(5,'Education investment - public/private/guild schools','N','Tests LS education quality vs state-run systems','','Skill accumulation','H')
add(5,'Health insurance - separate risk pool for medical','P','InsuranceMarket exists but covers all risks together','Insurance module','Insurance module','VH')
add(5,'Disability/long-term care - permanent non-earners','S','AGENT_MODEL.md mentions disability probability','AGENT_MODEL.md','Retiree module','M')
add(5,'Intergenerational wealth tracking - dynastic persistence','N','Tests if LS enables mobility or creates dynastic wealth','','Inheritance mechanic','L')
add(5,'Criminal liability - tort-based crime resolution','S','ARCHITECTURE.md crime via private tort framework','ARCHITECTURE.md','Court module','VH')
# Environment
add(6,'Pollution tort - firms pay for damage via courts','S','ARCHITECTURE.md Environmental harm definition','ARCHITECTURE.md','Court module','M')
add(6,'Carbon pricing - tax or cap-and-trade','N','Compares carbon pricing across all 10 systems','','Tax module','M')
add(6,'Natural resource commons - depletion with property rights','S','ARCHITECTURE.md Commons Stewardship section','ARCHITECTURE.md','None','H')
add(6,'Climate change - gradual warming, extreme weather','N','Long-horizon stress test for insurance markets','','Event system','VH')
add(6,'Renewable energy investment - green tech adoption','N','Tests if LS accelerates or delays green transition','','Business agent','H')
add(6,'Waste/circular economy - recycling, disposal costs','N','Growing real-world economic concern','','None','M')
add(6,'Biodiversity valuation - ecosystem service pricing','N','Frontier topic; tests LS property rights framework','','None','VH')
add(6,'Water rights/fisheries - common pool without authority','S','ARCHITECTURE.md Aquifer extraction, Fisheries','ARCHITECTURE.md','Court module','H')
add(6,'Nuisance liability - noise, light, odor as torts','S','EVENT_MODEL.md mentions nuisance liability','EVENT_MODEL.md','Court module','L')
add(6,'Pandemic - contagious illness with public externalities','S','EVENT_MODEL.md Pandemic shock, not coded','EVENT_MODEL.md','Event system','VH')
# Technology
add(7,'Endogenous R&D - firms invest in stochastic innovation','N','Tests if LS framework encourages or discourages R&D','','Business agent','H')
add(7,'Harberger patents - IP self-assessed, buyable','S','Future_Ideas doc mentions Harberger patent framework','Future_Ideas','Harberger market','M')
add(7,'Automation/AI displacement - tech eliminates jobs','S','EVENT_MODEL.md Technology Disruption shock, not coded','EVENT_MODEL.md','Event system','H')
add(7,'Knowledge spillovers - one firms R&D benefits others','N','Core endogenous growth mechanism','','Endogenous R&D','H')
add(7,'Network effects - value grows with user base','N','Enables natural monopoly; LS antitrust via liability','','Monopolization module','H')
add(7,'Platform economy - multi-sided digital markets','N','Tests LS liability framework for platforms','','Network effects','VH')
add(7,'Data property rights - own and license personal data','N','LS framework for privacy; property rights in data','','None','H')
add(7,'Technology adoption lags - heterogeneous adoption rate','N','Realistic productivity dispersion across firms','','Business agent','M')
add(7,'Algorithmic collusion - AI price coordination','N','Frontier antitrust; LS liability for tacit collusion','','Monopoly + adversarial','VH')
add(7,'Open-source commons - voluntary public good production','N','Alternative to market-based production','','None','M')
# International
add(8,'Inter-compact trade - comparative advantage flows','N','Tests if LS compacts trade more/less than US states','','Compact + business','H')
add(8,'Tariffs/trade barriers - compact-level import taxes','N','Tests if compact competition leads to protectionism','','Inter-compact trade','M')
add(8,'War Escrow defense - PMC funding, invasion defense','S','ARCHITECTURE.md Defense section, War Escrow NOT CODED','ARCHITECTURE.md','Compact + events','VH')
add(8,'Foreign direct investment - external capital flows','N','Crucial for international competitiveness analysis','','Equity market','H')
add(8,'Treaty/alliance system - compacts form blocs','S','ARCHITECTURE.md Alliance functions, not coded','ARCHITECTURE.md','Compact governance','VH')
add(8,'Economic sanctions - compacts penalize each other','N','Escalation dynamics within LS federation','','Compact governance','M')
add(8,'Currency union - shared money across compacts','N','Tests monetary stability without central bank','','Banking','H')
add(8,'Refugee/asylum shock - external population inflow','S','EVENT_MODEL.md Population Shock, incomplete','EVENT_MODEL.md','Event system','H')
add(8,'Inter-compact arbitration - dispute resolution','S','ARCHITECTURE.md Supreme Trust Oracle, not coded','ARCHITECTURE.md','Court module','M')
add(8,'Development aid - richer compacts help poorer','N','Tests if LS reduces inter-compact inequality','','Compact governance','L')
# Validation
add(9,'Historical backtesting - US 1960-2020 vs real GDP/Gini','N','THE single most critical missing validation step','','Calibration module','H')
add(9,'Global sensitivity analysis - all parameters +-50%','N','Identifies fragile vs robust findings','','None','M')
add(9,'Monte Carlo uncertainty - distributions not point estimates','N','Honest uncertainty quantification','','Sensitivity analysis','M')
add(9,'Laffer curve validation - tax revenue peaks at realistic rate','N','Minimal credibility test; currently completely untested','','None','L')
add(9,'Kuznets curve pattern - inequality over development','N','Validates model inequality dynamics are realistic','','None','L')
add(9,'Phillips curve - inflation-unemployment tradeoff','N','Validates model macro dynamics are realistic','','Central bank module','M')
add(9,'External peer review - publish methodology for scrutiny','N','Gold standard for scientific credibility','','Documentation','L')
add(9,'Comparative statics validation - match known elasticities','N','Validates individual mechanism correctness','','Calibration module','M')
add(9,'Out-of-sample testing - calibrate 60-90, test 90-2020','N','Detects overfitting','','Historical backtesting','M')
add(9,'Adversarial parameter testing - extreme values','P','Phase 4 has min/max clamping, no formal adversarial test','Phase 4','None','L')
# Engineering
add(10,'YAML config files - replace opaque _mk() tuples','N','Current system configs are fragile positional numbers','comparison_phase4.py','None','L')
add(10,'Real-time web dashboard - live charts, parameter sliders','N','Interactive exploration of parameter space','','None','H')
add(10,'Jupyter notebook API - documented Python import','N','Enables rapid prototyping of new dynamics','','Docstring API','M')
add(10,'Regression test suite - 500+ tests across all mechanics','P','Currently 21 tests in test_phase4_dynamics.py','test_phase4_dynamics.py','None','M')
add(10,'SQLite output database - structured cross-run querying','N','Flat JSON limits analysis depth','','None','L')
add(10,'Multi-CPU parallel execution - multiprocessing seeds','N','50 sims in 3s good; 500+ would benefit','','None','L')
add(10,'Genetic parameter optimization - Pareto frontier search','N','Discovers non-obvious optimal system designs','','Sensitivity analysis','H')
add(10,'Complete API reference - all config keys, return schemas','N','Current docstrings are minimal','comparison_phase4.py','None','L')
add(10,'Docker container - pinned deps, one-command reproducibility','N','Scientific reproducibility','','None','L')
add(10,'Property-based testing - invariant verification','N','Catches bugs unit tests miss (money conservation)','','None','H')

# Stats
new_c = sum(1 for i in items if '🆕' in i)
spec_c = sum(1 for i in items if '📋' in i)
part_c = sum(1 for i in items if '⚠️' in i)
low_c = sum(1 for i in items if '| Low |' in i)
med_c = sum(1 for i in items if '| Medium |' in i)
high_c = sum(1 for i in items if '| High |' in i)
vh_c = sum(1 for i in items if '| Very High |' in i)

header = '''# Liability State Simulator — 100 Improvements with Codebase Cross-Reference

*Tagged: NEW (not in codebase), SPEC (designed but not built), PARTIAL (exists but incomplete)*
*Source = existing file where concept is documented. Dep = what must be built first.*

| # | Cat | Status | Improvement | Rationale | Source | Dep | Cost |
|---|-----|--------|-------------|----------|--------|-----|------|
'''

footer = f'''
## Statistics
- **{new_c}** novel (not in codebase)
- **{spec_c}** spec'd but not implemented
- **{part_c}** partially implemented
- Cost: Low={low_c}, Medium={med_c}, High={high_c}, Very High={vh_c}

## Top Priority by Impact
1. **Harberger self-assessment (#21)** — LS core mechanism; mechanics/harberger.py EXISTS but never wired into comparison
2. **War Escrow defense (#73)** — Core LS institution; full spec in ARCHITECTURE.md but zero code
3. **Compact governance/voting (#31)** — Enables endogenous policy; unlocks 10+ dependent improvements
4. **Historical backtesting (#81)** — Without validation against real data, all rankings are provisional
5. **Fractional-reserve banking (#11)** — Credit cycles; tests LS stability claims vs traditional systems

## Quick Wins (Low Cost, No Dependencies)
'''.strip()

quick = ', '.join(f'#{i+1}' for i, item in enumerate(items) if '| Low |' in item)

with open('100_improvements.md', 'w') as f:
    f.write(header + '\n')
    for item in items:
        f.write(item + '\n')
    f.write('\n' + footer + '\n' + quick + '\n')

print(f'Generated: {len(items)} improvements')
print(f'NEW={new_c} SPEC={spec_c} PARTIAL={part_c}')
print(f'Cost: L={low_c} M={med_c} H={high_c} VH={vh_c}')
print('Output: 100_improvements.md')
