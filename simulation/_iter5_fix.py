# Final adjustments: Germany (reduce reuni/hartz to get STABLE) and India (adjust wage_disp to get STABLE)
import sys; sys.path.insert(0, 'src')
from comparison_phase8 import run_phase8, gen_population

print("=== GERMANY FIX ===")
# Try lower reuni/hartz
for reuni, hartz in [(0.5, 0.3), (0.3, 0.2), (0.2, 0.1), (0.0, 0.0)]:
    de_60 = dict(tax_type='income', income_tax_rate=0.35, corp_tax_rate=0.50, welfare_rate=0.06,
                 healthcare_gdp_share=0.05, skill_premium_growth=0.005, union_coverage=0.30,
                 capital_income_share=0.05, import_competition=0.02, wage_dispersion_mult=1.2,
                 inheritance_rate=0.0)
    de_20 = dict(tax_type='income', income_tax_rate=0.40, corp_tax_rate=0.15, welfare_rate=0.13,
                 healthcare_gdp_share=0.10, skill_premium_growth=0.012, union_coverage=0.22,
                 capital_income_share=0.12, import_competition=0.12,
                 reunification_shock=reuni, hartz_reform=hartz,
                 wage_dispersion_mult=1.5, inheritance_rate=0.0)
    w,r,b = gen_population(42)
    r60 = run_phase8(w,r,b,42, dict(de_60, system_name='DE_60'))
    w2,r2,b2 = gen_population(42)
    r20 = run_phase8(w2,r2,b2,42, dict(de_20, system_name='DE_20'))
    delta = r20['gini'] - r60['gini']
    trend = 'STABLE' if abs(delta) <= 0.02 else ('RISING' if delta > 0 else 'FALLING')
    print("  reuni={:.1f} hartz={:.1f}: 1960s={:.4f} 2020s={:.4f} delta={:+.4f} trend={} {}".format(
        reuni, hartz, r60['gini'], r20['gini'], delta, trend,
        "PASS" if trend == 'STABLE' else 'FAIL'))

print()
print("=== INDIA FIX ===")
for wd_70, wd_20 in [(3.0, 3.0), (3.5, 3.0), (3.0, 2.5), (3.5, 2.5)]:
    in_70 = dict(tax_type='income', income_tax_rate=0.15, corp_tax_rate=0.55, welfare_rate=0.02,
                 healthcare_gdp_share=0.02, elite_capture_intensity=0.35,
                 informal_share=0.85, informal_wage_penalty=0.4, wage_dispersion_mult=wd_70,
                 inheritance_rate=0.0)
    in_20 = dict(tax_type='income', income_tax_rate=0.25, corp_tax_rate=0.25, welfare_rate=0.08,
                 healthcare_gdp_share=0.04, elite_capture_intensity=0.35,
                 skill_premium_growth=0.015, capital_income_share=0.20, import_competition=0.25,
                 informal_share=0.80, informal_wage_penalty=0.4, wage_dispersion_mult=wd_20,
                 inheritance_rate=0.0)
    w,r,b = gen_population(42)
    r70 = run_phase8(w,r,b,42, dict(in_70, system_name='IN_70'))
    w2,r2,b2 = gen_population(42)
    r20 = run_phase8(w2,r2,b2,42, dict(in_20, system_name='IN_20'))
    delta = r20['gini'] - r70['gini']
    trend = 'STABLE' if abs(delta) <= 0.02 else ('RISING' if delta > 0 else 'FALLING')
    print("  wd70={:.1f} wd20={:.1f}: 1970s={:.4f} 2020s={:.4f} delta={:+.4f} trend={} {}".format(
        wd_70, wd_20, r70['gini'], r20['gini'], delta, trend,
        "PASS" if trend == 'STABLE' else 'FAIL'))
