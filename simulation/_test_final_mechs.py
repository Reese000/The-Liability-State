import sys; sys.path.insert(0, 'src')
from comparison_phase8 import run_phase8, gen_population, PHASE8_CONFIGS
import numpy as np

print("=== BUSINESS PROFIT FIX + NEW MECHANISMS ===")
print()

# 1. Baseline — all OFF should still be backward compatible
print("1. BACKWARD COMPATIBILITY (all OFF)")
for name in ['LS_Full', 'US_Style', 'Nordic', 'Laissez_Faire']:
    w, r, b = gen_population(42)
    res = run_phase8(w, r, b, 42, PHASE8_CONFIGS[name])
    print(f"  {name}: Gini={res['gini']:.4f} Mean=${res['w_mean']:,.0f} Wealth=${res['wealth']:,}")

print()
print("2. CAPITAL INCOME CONCENTRATION (now with business profit!)")
base = PHASE8_CONFIGS['US_Style']
w, r, b = gen_population(42)
r0 = run_phase8(w, r, b, 42, base)
print(f"  Baseline (no cap income):         Gini={r0['gini']:.4f}")

for conc in [0.1, 0.3, 0.5]:
    cfg = dict(base, capital_income_concentration=conc, capital_income_top_share=0.1)
    w, r, b = gen_population(42)
    res = run_phase8(w, r, b, 42, cfg)
    dg = res['gini'] - r0['gini']
    print(f"  conc={conc:.1f} top=10%:               Gini={res['gini']:.4f} (Δ{dg:+.4f})")

# Vary top share
print("  Varying top share (conc=0.3):")
for top in [0.01, 0.05, 0.10, 0.20]:
    cfg = dict(base, capital_income_concentration=0.3, capital_income_top_share=top)
    w, r, b = gen_population(42)
    res = run_phase8(w, r, b, 42, cfg)
    print(f"    top {top*100:.0f}%: Gini={res['gini']:.4f} (Δ{res['gini']-r0['gini']:+.4f})")

print()
print("3. INHERITANCE (bequest)")
cfg_orig = dict(base, inheritance_rate=0.3, inherit_bequest=False)
cfg_beq = dict(base, inheritance_rate=0.3, inherit_bequest=True)
w, r, b = gen_population(42)
r_orig = run_phase8(w, r, b, 42, cfg_orig)
w2, r2, b2 = gen_population(42)
r_beq = run_phase8(w2, r2, b2, 42, cfg_beq)
print(f"  Original (equal):       Gini={r_orig['gini']:.4f} (compresses)")
print(f"  Bequest (realistic):    Gini={r_beq['gini']:.4f} (widens)")
print(f"  Difference:             Δ={r_beq['gini'] - r_orig['gini']:+.4f}")

print()
print("4. COMBINED EFFECT: US_Style toward actual US Gini (0.48)")
cfg_all = dict(base,
    capital_income_concentration=0.3, capital_income_top_share=0.10,
    inheritance_rate=0.3, inherit_bequest=True,
    skill_premium_growth=0.015, union_coverage=0.12,
    capital_income_share=0.15, import_competition=0.20,
    use_progressive_tax=True, elite_capture_intensity=0.15,
    wage_dispersion_mult=2.0)
w, r, b = gen_population(42)
r_all = run_phase8(w, r, b, 42, cfg_all)
gap_before = 0.48 - r0['gini']
gap_after = 0.48 - r_all['gini']
pct_closed = (1 - gap_after / gap_before) * 100
print(f"  Baseline Gini:                {r0['gini']:.4f}")
print(f"  After all mechanisms:         {r_all['gini']:.4f}")
print(f"  Actual US Gini:               0.48")
print(f"  Gap closed:                   {pct_closed:.1f}%")

print()
print("5. FRANCE WITH CAPITAL INCOME")
cfg_fr = dict(tax_type='income', income_tax_rate=0.45, corp_tax_rate=0.25, welfare_rate=0.20,
              healthcare_gdp_share=0.11, use_progressive_tax=True, child_benefit_taper=0.50,
              unemployment_rate=0.08, informal_share=0.12, wage_dispersion_mult=2.0,
              capital_income_concentration=0.2, capital_income_top_share=0.10,
              skill_premium_growth=0.008, union_coverage=0.25, capital_income_share=0.12,
              import_competition=0.15, elite_capture_intensity=0.05)
w, r, b = gen_population(42)
r_fr = run_phase8(w, r, b, 42, dict(cfg_fr, system_name='FR'))
print(f"  France 2020s: Gini={r_fr['gini']:.4f} Actual=0.30 Delta={r_fr['gini']-0.30:+.4f}")

print()
print("=== VERIFICATION COMPLETE ===")
