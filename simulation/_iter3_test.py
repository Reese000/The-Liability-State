import sys; sys.path.insert(0, 'src')
from comparison_phase8 import run_phase8, gen_population

print("=== CHINA: period-varying informal_share + SBTC ===")
print("China actual Gini trajectory: 0.28(1980s) -> 0.43(2000s) -> 0.36(2020s)")
print()

# China 1980s: pre-reform, low inequality, low informal
china_1980 = dict(tax_type='income', income_tax_rate=0.05, corp_tax_rate=0.55, welfare_rate=0.01,
                  healthcare_gdp_share=0.02, informal_share=0.05,  # Pre-reform: low informal
                  skill_premium_growth=0.002, union_coverage=0.40,  # High union (danwei system)
                  capital_income_share=0.05, import_competition=0.02,
                  elite_capture_intensity=0.05, wage_dispersion_mult=1.0,
                  inheritance_rate=0.0)

# China 2000s: post-SOE reform, high informal, high inequality
china_2000 = dict(tax_type='income', income_tax_rate=0.10, corp_tax_rate=0.33, welfare_rate=0.03,
                  healthcare_gdp_share=0.03, informal_share=0.35,  # Mass layoffs, rural migrants
                  skill_premium_growth=0.015, union_coverage=0.15,  # Union decline
                  capital_income_share=0.20, import_competition=0.15,
                  elite_capture_intensity=0.20, wage_dispersion_mult=1.5,
                  inheritance_rate=0.0)

# China 2020s: welfare expansion, hukou reform beginning
china_2020 = dict(tax_type='income', income_tax_rate=0.15, corp_tax_rate=0.25, welfare_rate=0.07,
                  healthcare_gdp_share=0.05, informal_share=0.25,  # Some reform
                  skill_premium_growth=0.012, union_coverage=0.15,
                  capital_income_share=0.22, import_competition=0.20,
                  elite_capture_intensity=0.25, wage_dispersion_mult=1.5,
                  inheritance_rate=0.0)

# Run
configs = [
    ("1980s", china_1980, 0.28),
    ("2000s", china_2000, 0.43),
    ("2020s", china_2020, 0.36),
]

w, r, b = gen_population(42)
ginis = []
for i, (label, cfg, actual) in enumerate(configs):
    res = run_phase8(w, r, b, 42 + i, dict(cfg, system_name='CHN_' + label))
    ginis.append(res['gini'])
    print("  {}: Sim={:.4f} Actual={:.2f} Delta={:+.4f}".format(label, res['gini'], actual, res['gini']-actual))

# Check period-to-period trends
print()
rise_80_00 = ginis[1] - ginis[0]
fall_00_20 = ginis[2] - ginis[1]
print("1980s->2000s: {:.4f} (expected RISING)".format(rise_80_00))
print("2000s->2020s: {:.4f} (expected FALLING)".format(fall_00_20))
print()
print("Rise-then-fall pattern: {}".format(
    "PASS" if rise_80_00 > 0.02 and fall_00_20 < -0.02 else "FAIL"))

# Try higher params
print()
print("=== TRYING HIGHER INFORMAL in 2000s ===")
for inf_2000, wd_2000 in [(0.40, 2.0), (0.45, 2.0), (0.40, 2.5)]:
    cfg2 = dict(china_2000, informal_share=inf_2000, wage_dispersion_mult=wd_2000)
    w,r,b = gen_population(42)
    res2 = run_phase8(w,r,b,44, dict(cfg2, system_name='CHN_2000v2'))
    rise = res2['gini'] - ginis[0]
    fall = ginis[2] - res2['gini']
    print("  inf={:.2f} wd={:.1f}: 2000s Gini={:.4f} rise={:+.4f} fall={:+.4f} {}".format(
        inf_2000, wd_2000, res2['gini'], rise, fall,
        "PASS" if rise > 0.02 and fall < -0.02 else "FAIL"))
