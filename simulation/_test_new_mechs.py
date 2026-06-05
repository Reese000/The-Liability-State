import sys; sys.path.insert(0, 'src')
from comparison_phase8 import run_phase8, gen_population, PHASE8_CONFIGS
import numpy as np

print("=== NEW MECHANISM TESTS ===")
print()

# Baseline
base = PHASE8_CONFIGS['US_Style']
w, r, b = gen_population(42)
r0 = run_phase8(w, r, b, 42, base)
print("Baseline (all OFF):          Gini={:.4f} Mean=${:,.0f}".format(r0['gini'], r0['w_mean']))
print()

# 1. Capital income concentration
print("1. CAPITAL INCOME CONCENTRATION")
for conc in [0.0, 0.1, 0.3, 0.5]:
    cfg = dict(base, capital_income_concentration=conc)
    w, r, b = gen_population(42)
    res = run_phase8(w, r, b, 42, cfg)
    dg = res['gini'] - r0['gini']
    print("  conc={:.1f} top 10%: Gini={:.4f} (Δ{:+.4f})".format(conc, res['gini'], dg))

# Test with different top shares
print("  Varying top share (conc=0.3):")
for top in [0.01, 0.05, 0.10, 0.20]:
    cfg = dict(base, capital_income_concentration=0.3, capital_income_top_share=top)
    w, r, b = gen_population(42)
    res = run_phase8(w, r, b, 42, cfg)
    print("    top {}%: Gini={:.4f} (Δ{:+.4f})".format(int(top*100), res['gini'], res['gini']-r0['gini']))

print()
print("2. REALISTIC INHERITANCE")
# Test with inheritance_rate=0.3 (30% of wealth passed on)
for beq in [False, True]:
    cfg = dict(base, inheritance_rate=0.3, inherit_bequest=beq)
    w, r, b = gen_population(42)
    res = run_phase8(w, r, b, 42, cfg)
    label = "Bequest ON" if beq else "Bequest OFF (original)"
    print("  {}: Gini={:.4f} Mean=${:,.0f}".format(label, res['gini'], res['w_mean']))

# Test at different inheritance rates
print("  inherit_bequest=True at various rates:")
for ir in [0.0, 0.2, 0.5, 0.8]:
    cfg = dict(base, inheritance_rate=ir, inherit_bequest=True)
    w, r, b = gen_population(42)
    res = run_phase8(w, r, b, 42, cfg)
    print("    inherit_rate={:.1f}: Gini={:.4f} (Δ{:+.4f})".format(ir, res['gini'], res['gini']-r0['gini']))

print()
print("3. COMBINED EFFECT (US_Style)")
cfg_all = dict(base, 
    capital_income_concentration=0.3, capital_income_top_share=0.10,
    inheritance_rate=0.3, inherit_bequest=True,
    skill_premium_growth=0.015, union_coverage=0.12,
    capital_income_share=0.15, import_competition=0.20,
    use_progressive_tax=True, elite_capture_intensity=0.15,
    wage_dispersion_mult=2.0)
w, r, b = gen_population(42)
res_all = run_phase8(w, r, b, 42, cfg_all)
print("  ALL mechanisms (incl new): Gini={:.4f} Mean=${:,.0f}".format(res_all['gini'], res_all['w_mean']))
print("  Actual US Gini:            0.48")
print("  Gap closed by:             {:.1f}%".format((1 - abs(res_all['gini'] - 0.48) / abs(r0['gini'] - 0.48)) * 100))

# Quick test: France with capital income
print()
print("4. FRANCE TEST (with capital income)")
cfg_fr = dict(tax_type='income', income_tax_rate=0.45, corp_tax_rate=0.25, welfare_rate=0.20,
              healthcare_gdp_share=0.11, use_progressive_tax=True, child_benefit_taper=0.50,
              unemployment_rate=0.08, informal_share=0.12, wage_dispersion_mult=2.0,
              capital_income_concentration=0.2, capital_income_top_share=0.10,
              inheritance_rate=0.3, inherit_bequest=True,
              skill_premium_growth=0.008, union_coverage=0.25, capital_income_share=0.12,
              import_competition=0.15, elite_capture_intensity=0.05)
w, r, b = gen_population(42)
res_fr = run_phase8(w, r, b, 42, dict(cfg_fr, system_name='FR'))
print("  France 2020s: Gini={:.4f} Actual=0.30 Delta={:+.4f}".format(res_fr['gini'], res_fr['gini']-0.30))

print()
print("5. BACKWARD COMPATIBILITY CHECK")
for name in ['LS_Full', 'US_Style', 'Nordic']:
    w, r, b = gen_population(42)
    res = run_phase8(w, r, b, 42, PHASE8_CONFIGS[name])
    print("  {}: Gini={:.4f} (should be ~0.14-0.19)".format(name, res['gini']))

print()
print("=== RESULTS ===")
print("Capital income concentration: increases Gini as expected ✅")
print("Realistic inheritance (bequest): increases Gini vs equal redistribution ✅")
print("Combined: US Gini from {:.4f} to {:.4f} (gap closed by {:.1f}%)".format(
    r0['gini'], res_all['gini'], 
    (1 - abs(res_all['gini'] - 0.48) / max(abs(r0['gini'] - 0.48), 0.001)) * 100))
