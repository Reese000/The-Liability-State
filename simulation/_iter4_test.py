import sys; sys.path.insert(0, 'src')
from comparison_phase8 import run_phase8, gen_population

print("=== INDIA: massive informal sector + wage dispersion ===")
print("India actual Gini: ~0.48 (WID.world pre-tax national income)")
print()

# India 1970s: very high informal
india_1970 = dict(tax_type='income', income_tax_rate=0.15, corp_tax_rate=0.55, welfare_rate=0.02,
                  healthcare_gdp_share=0.02, elite_capture_intensity=0.35,
                  informal_share=0.85, informal_wage_penalty=0.4,  # 85% informal, 40% wage
                  wage_dispersion_mult=3.0,  # Very wide wage distribution
                  inheritance_rate=0.0)

# India 2020s: slightly lower informal
india_2020 = dict(tax_type='income', income_tax_rate=0.25, corp_tax_rate=0.25, welfare_rate=0.08,
                  healthcare_gdp_share=0.04, elite_capture_intensity=0.35,
                  skill_premium_growth=0.015, capital_income_share=0.20,
                  import_competition=0.25, informal_share=0.80,
                  informal_wage_penalty=0.4, wage_dispersion_mult=3.0,
                  inheritance_rate=0.0)

w, r, b = gen_population(42)
res_70 = run_phase8(w, r, b, 42, dict(india_1970, system_name='IN_1970'))
print("India 1970s:")
print("  Sim Gini={:.4f} Actual=0.48 Delta={:+.4f}".format(res_70['gini'], res_70['gini']-0.48))

w2, r2, b2 = gen_population(42)
res_20 = run_phase8(w2, r2, b2, 42, dict(india_2020, system_name='IN_2020'))
print("India 2020s:")
print("  Sim Gini={:.4f} Actual=0.48 Delta={:+.4f}".format(res_20['gini'], res_20['gini']-0.48))

delta = res_20['gini'] - res_70['gini']
trend = 'RISING' if delta > 0.02 else ('FALLING' if delta < -0.02 else 'STABLE')
print("Trend: sim={}, actual=STABLE {}".format(trend, "PASS" if trend == 'STABLE' else 'FAIL'))
print()

# Try higher wage_disp
print("=== TRYING HIGHER WAGE DISP ===")
for wd in [3.0, 4.0, 5.0, 6.0]:
    cfg = dict(india_2020, wage_dispersion_mult=wd)
    w,r,b = gen_population(42)
    res = run_phase8(w,r,b,42, dict(cfg, system_name='IN_wd{}'.format(wd)))
    print("  wd={:.0f}: Gini={:.4f} Delta={:+.4f}".format(wd, res['gini'], res['gini']-0.48))

# Try lower informal_wage_penalty
print()
print("=== TRYING LOWER INFORMAL WAGE PENALTY ===")
for pen in [0.4, 0.3, 0.2]:
    cfg = dict(india_2020, informal_wage_penalty=pen, wage_dispersion_mult=4.0)
    w,r,b = gen_population(42)
    res = run_phase8(w,r,b,42, dict(cfg, system_name='IN_pen{}'.format(pen)))
    print("  pen={:.1f} wd=4.0: Gini={:.4f} Delta={:+.4f}".format(pen, res['gini'], res['gini']-0.48))
