#!/usr/bin/env python3
"""
comparison_models.py — Historical socioeconomic parameter data for Japan, Brazil, France.

Provides COUNTRY_DATA dict matching the HISTORICAL_DATA format used in
validate_backtest_historical.py, extended with Phase 8 sectoral and inequality
mechanism keys for comparison_phase8.py compatibility.

Sources cited per-country.  Primary references:
  - OECD Tax Revenue Database (https://stats.oecd.org)
  - World Bank World Development Indicators
  - Piketty & Saez "World Inequality Database" (WID.world)
  - ICTWSS (Database on Institutional Characteristics of Trade Unions)
  - Piketty, T. "Capital in the 21st Century" (2014)
  - Atkinson, A.B. "Inequality: What Can Be Done?" (2015)
  - Alvaredo et al. "World Inequality Report" (2018/2022)
  - OECD "Taxing Wages" series
  - OECD Health Statistics / Education at a Glance
  - Heritage Foundation / Fraser Institute (tax burden indices)

Usage:
    from comparison_models import COUNTRY_DATA, get_period_config, print_summary
"""

# ═══════════════════════════════════════════════════════════════════════════
#  COUNTRY DATA — Japan, Brazil, France
# ═══════════════════════════════════════════════════════════════════════════
# Structure per country:
#   'system_label':  Human-readable name
#   'actual_tax_gdp': dict {year: tax_revenue_as_percent_of_GDP}
#   'actual_tax_gdp_source': string
#   'periods': dict {year: {parameter_values}}
#
# Period parameters follow the param_map from validate_backtest_historical.py:
#   income_tax      → income_tax_rate  (0.0–0.7)
#   corp_tax        → corp_tax_rate    (0.0–0.55)
#   welfare         → welfare_rate     (0.0–0.3, fraction of tax revenue)
#   healthcare      → healthcare_gdp_share (0.0–0.2)
#   education       → education_gdp_share (0.0–0.1)
#   carbon_tax      → carbon_tax_rate  (0.0–0.05, fraction of business revenue)
#   union_premium   → union_premium    (0.8–1.3)
#   cpf             → cpf_rate         (0.0–0.4)
#   elite_capture   → elite_capture_intensity (0.0–0.5)
#   gini_actual     → historical Gini for validation
#
# Phase 8c inequality mechanisms (all default OFF in the engine):
#   skill_premium_growth  → annual SBTC premium (0.0–0.02)
#   union_coverage        → union coverage rate (0.0–1.0)
#   capital_income_share  → financialization share (0.0–0.3)
#   import_competition    → import competition intensity (0.0–0.5)
#   use_progressive_tax   → True/False
# ═══════════════════════════════════════════════════════════════════════════

COUNTRY_DATA = {

    # ─────────────────────────────────────────────────────────────────────
    #  JAPAN
    # ─────────────────────────────────────────────────────────────────────
    # Key characteristics:
    #   - Low inequality historically (post-war land reform, strong unions)
    #   - Very low healthcare spending despite universal coverage (regulated
    #     fees, ~8% GDP vs 11-18% in other advanced economies)
    #   - Corporate tax rates fell from ~50% (1980s) to ~30% (2020s)
    #   - Union coverage declined from ~35% (1960s) to ~17% (2020s)
    #   - Aging population pressure drove consumption tax from 0→10%
    #   - Income inequality (Gini) rose post-1990s "lost decade"
    #
    # Sources:
    #   [1] OECD Tax Revenue Database (2024)
    #   [2] WID.world (World Inequality Database) — Gini series
    #   [3] Ministry of Finance Japan — tax history
    #   [4] OECD Health Statistics 2024
    #   [5] ICTWSS 6.1 — union coverage data
    #   [6] Piketty & Saez (2003) — top income shares
    #   [7] Ohtake (2008) — Japan's inequality since 1980s
    #   [8] Tax Policy Center — Japan corporate tax history
    #   [9] OECD Education at a Glance
    #   [10] World Bank WDI — Gini estimates
    # ─────────────────────────────────────────────────────────────────────
    'Japan': {
        'system_label': 'Japan',

        # Total tax revenue as % of GDP (all levels of government)
        # Source: OECD Tax Revenue Database [1]
        'actual_tax_gdp': {
            1960: 18,   # Post-war, low tax base
            1980: 25,   # Bubble era, rising revenue
            2000: 27,   # Post-bubble, consumption tax introduced (3%)
            2020: 32,   # Consumption tax raised to 10%, aging costs
        },
        'actual_tax_gdp_source': 'OECD Tax Revenue Database, Japan [1]',

        'periods': {
            # ── 1960s: High-growth era ──────────────────────────────────
            # Income tax: low post-war rates, top rate ~50% but narrow base
            # Corporate tax: ~42% effective
            # Welfare: nascent, ~1-2% of revenue
            # Healthcare: low (universal system established 1961)
            # Carbon tax: non-existent
            # Union premium: moderate (strong enterprise unions)
            # Union coverage: ~35% density [5]
            # Skill premium growth: low (egalitarian education system)
            # Import competition: low (protected domestic market)
            # Capital income share: low (post-war egalitarian settlement)
            1960: {
                'income_tax': 0.15,        # Effective ~15% (OECD [1])
                'corp_tax': 0.42,           # ~42% effective corporate rate [8]
                'welfare': 0.04,            # Nascent welfare state
                'healthcare': 0.03,         # ~3% GDP (system just established) [4]
                'education': 0.04,          # ~4% GDP [9]
                'carbon_tax': 0.0,
                'union_premium': 1.12,      # Strong enterprise unions
                'cpf': 0.0,                 # No CPF system
                'elite_capture': 0.05,      # Low elite capture
                'gini_actual': 0.35,        # WID.world / Ohtake [2][7]
                # Inequality mechanism keys
                'skill_premium_growth': 0.001,   # Low SBTC
                'union_coverage': 0.35,          # ~35% union density [5]
                'capital_income_share': 0.10,    # Low financialization
                'import_competition': 0.05,      # Protected economy
                'use_progressive_tax': True,
            },

            # ── 1980s: Bubble era ──────────────────────────────────────
            # Income tax: moderate, top rates ~50-60%, but many deductions
            # Corporate tax: ~50% (high)
            # Welfare: expanding (aging starting)
            # Healthcare: cost controls effective
            # Gini: still low but starting to rise
            1980: {
                'income_tax': 0.25,        # Effective ~25% [1]
                'corp_tax': 0.50,           # ~50% effective rate [8]
                'welfare': 0.08,            # Expanding welfare
                'healthcare': 0.06,         # ~6% GDP [4]
                'education': 0.05,          # ~5% GDP [9]
                'carbon_tax': 0.0,
                'union_premium': 1.10,      # Strong but declining
                'cpf': 0.0,
                'elite_capture': 0.08,
                'gini_actual': 0.36,        # Rising slightly [7]
                # Inequality mechanism keys
                'skill_premium_growth': 0.003,
                'union_coverage': 0.28,          # Declining [5]
                'capital_income_share': 0.15,    # Bubble-era finance
                'import_competition': 0.08,
                'use_progressive_tax': True,
            },

            # ── 2000s: Lost decade aftermath ────────────────────────────
            # Consumption tax introduced 1989 (3%), raised to 5% in 1997
            # Income tax: rates cut to stimulate economy
            # Corporate tax: falling from 50%→42%
            # Welfare: rising (aging society, pensions)
            # Gini: notably rising post-bubble
            2000: {
                'income_tax': 0.22,        # Effective ~22% [1]
                'corp_tax': 0.42,           # Reduced to ~42% [8]
                'welfare': 0.12,            # Rising pension costs
                'healthcare': 0.08,         # ~8% GDP [4]
                'education': 0.04,          # ~4% GDP [9]
                'carbon_tax': 0.002,        # Very low petroleum tax
                'union_premium': 1.08,
                'cpf': 0.0,
                'elite_capture': 0.12,      # Rising elite wealth
                'gini_actual': 0.39,        # OECD [1], WID.world [2]
                # Inequality mechanism keys
                'skill_premium_growth': 0.005,
                'union_coverage': 0.20,          # [5]
                'capital_income_share': 0.20,    # Rising financial share
                'import_competition': 0.15,      # Import penetration growing
                'use_progressive_tax': True,
            },

            # ── 2020s: Current era ──────────────────────────────────────
            # Consumption tax at 10% (from 2019)
            # Corporate tax: ~30% effective (competitive)
            # Healthcare: controlled at ~10.9% GDP (lowest among G7)
            # Welfare: high due to super-aging
            # Gini: moderate compared to US/UK, but elevated
            2020: {
                'income_tax': 0.30,        # Effective ~30% (incl. consumption tax effects)
                'corp_tax': 0.30,           # ~30% effective rate [8]
                'welfare': 0.18,            # Pension & healthcare transfers
                'healthcare': 0.11,         # ~11% GDP, still low by OECD [4]
                'education': 0.03,          # ~3.5% GDP [9]
                'carbon_tax': 0.003,        # Low carbon price (~$2/ton)
                'union_premium': 1.05,      # Weakened unions
                'cpf': 0.0,
                'elite_capture': 0.18,      # Rising inequality of top wealth
                'gini_actual': 0.40,        # OECD ~0.40 [1], WID ~0.39 [2]
                # Inequality mechanism keys
                'skill_premium_growth': 0.008,
                'union_coverage': 0.17,          # [5]
                'capital_income_share': 0.22,    # Moderate financialization
                'import_competition': 0.20,      # Open economy
                'use_progressive_tax': True,
            },
        },
    },

    # ─────────────────────────────────────────────────────────────────────
    #  BRAZIL
    # ─────────────────────────────────────────────────────────────────────
    # Key characteristics:
    #   - One of the highest Gini coefficients in the world (0.53-0.60)
    #   - High tax burden (~33% GDP) for an emerging economy
    #   - Complex, regressive tax structure (high consumption taxes)
    #   - Moderate corporate tax (~34%) but high compliance costs
    #   - Inegalitarian post-WWII development path
    #   - Military regime (1964-1985) → democratic consolidation
    #   - Very high union coverage in formal sector (~50% in 1980s)
    #   - High elite capture / informality
    #
    # Sources:
    #   [1] OECD Tax Revenue Database, Brazil country profile
    #   [2] WID.world — Brazil Gini series
    #   [3] IPEA (Brazilian Institute for Applied Economic Research)
    #   [4] World Bank WDI — Brazil Gini estimates
    #   [5] OECD Brazil Economic Surveys
    #   [6] Piketty & Saez (2015) — Brazil inequality
    #   [7] Souza (2018) — "A History of Inequality" (Brazil)
    #   [8] ICTWSS — union data (where available)
    #   [9] IBGE — Brazilian Institute of Geography and Statistics
    #   [10] Afonso & Araujo (2017) — Brazilian tax structure
    # ─────────────────────────────────────────────────────────────────────
    'Brazil': {
        'system_label': 'Brazil',

        # Total tax revenue as % of GDP
        # Source: OECD Tax Revenue Database, Brazil [1]
        # Brazil's tax burden rose steadily from ~20% GDP in 1960s
        # to ~33% GDP by 2020s.
        'actual_tax_gdp': {
            1960: 17,   # Underdeveloped tax state
            1980: 24,   # Military regime industrial policy
            2000: 30,   # Post-democratization, welfare expansion
            2020: 33,   # High by emerging-market standards [1]
        },
        'actual_tax_gdp_source': 'OECD Tax Revenue Database, Brazil; IPEA [1][3]',

        'periods': {
            # ── 1960s: Pre-military regime / early industrial ──────────
            # Tax system: underdeveloped, narrow base
            # Inequality: extremely high (post-slavery legacy)
            # Union coverage: urban formal sector unions growing
            # Elite capture: very high (landowners, industrial oligarchy)
            1960: {
                'income_tax': 0.15,        # Narrow base, low effective rate
                'corp_tax': 0.30,           # Moderate corporate rate
                'welfare': 0.05,            # Limited social security
                'healthcare': 0.02,         # Minimal public health spending
                'education': 0.02,          # Low education investment
                'carbon_tax': 0.0,
                'union_premium': 1.15,      # Strong sectoral unions
                'cpf': 0.0,
                'elite_capture': 0.35,      # Very high elite dominance
                'gini_actual': 0.57,        # Very high inequality [4][7]
                # Inequality mechanism keys
                'skill_premium_growth': 0.005,
                'union_coverage': 0.20,          # Formal sector only [8]
                'capital_income_share': 0.25,    # Concentrated capital
                'import_competition': 0.10,      # Import substitution era
                'use_progressive_tax': False,    # Regressive system
            },

            # ── 1980s: Military regime / "Lost Decade" ─────────────────
            # High inflation, debt crisis
            # Tax system: growing (military developmental state)
            # Gini: still extremely high
            # Union coverage: rising (democratic transition)
            1980: {
                'income_tax': 0.18,        # Slightly higher effective rate
                'corp_tax': 0.35,           # ~35% corporate rate
                'welfare': 0.08,            # Expanding social security
                'healthcare': 0.03,         # Still low public health
                'education': 0.03,          # Still low
                'carbon_tax': 0.0,
                'union_premium': 1.20,      # Strong syndicalist unions
                'cpf': 0.0,
                'elite_capture': 0.40,      # Very high
                'gini_actual': 0.60,        # Peak inequality [4][7]
                # Inequality mechanism keys
                'skill_premium_growth': 0.008,
                'union_coverage': 0.30,          # Rising coverage [8]
                'capital_income_share': 0.28,
                'import_competition': 0.08,      # Closed economy
                'use_progressive_tax': False,
            },

            # ── 2000s: Post-democratization / Lula era ─────────────────
            # Tax burden peaked around 32-34% GDP
            # Moderate corporate tax (~34%)
            # Social programs expanded (Bolsa Família)
            # Gini declining for first time in decades
            # Strong formal sector unions
            2000: {
                'income_tax': 0.22,        # Growing effective income tax
                'corp_tax': 0.34,           # ~34% (including social contributions) [10]
                'welfare': 0.15,            # Bolsa Família, expanded social security
                'healthcare': 0.04,         # SUS (unified health system) ~4% GDP
                'education': 0.05,          # Rising to ~5% GDP
                'carbon_tax': 0.0,
                'union_premium': 1.18,
                'cpf': 0.0,
                'elite_capture': 0.30,      # Somewhat reduced by social policy
                'gini_actual': 0.57,        # Still very high but declining [4]
                # Inequality mechanism keys
                'skill_premium_growth': 0.010,
                'union_coverage': 0.35,          # Formal sector strength [8]
                'capital_income_share': 0.25,
                'import_competition': 0.15,      # Opening economy
                'use_progressive_tax': True,     # Some progressivity added
            },

            # ── 2020s: Current era ─────────────────────────────────────
            # Tax burden ~33% GDP
            # Corporate tax ~34% effective
            # Very high informality (40%+ of workers)
            # Gini declining slowly but still >0.50
            # High elite capture via complex tax system
            # Low unionization (~15% effective)
            2020: {
                'income_tax': 0.25,        # Effective income tax [1]
                'corp_tax': 0.34,           # Corporate + social contributions [10]
                'welfare': 0.16,            # Bolsa Família / Auxílio Brasil
                'healthcare': 0.05,         # SUS ~4.5% GDP
                'education': 0.06,          # ~6% GDP
                'carbon_tax': 0.0,
                'union_premium': 1.10,      # Weakened formal unions
                'cpf': 0.0,
                'elite_capture': 0.35,      # Persistent high elite capture
                'gini_actual': 0.53,        # WID.world [2], World Bank [4]
                # Inequality mechanism keys
                'skill_premium_growth': 0.012,
                'union_coverage': 0.25,          # Formal sector [8]
                'capital_income_share': 0.28,
                'import_competition': 0.20,      # Open economy
                'use_progressive_tax': False,    # Regressive overall
            },
        },
    },

    # ─────────────────────────────────────────────────────────────────────
    #  FRANCE
    # ─────────────────────────────────────────────────────────────────────
    # Key characteristics:
    #   - High tax burden (among highest in OECD, ~45-47% GDP)
    #   - Strong welfare state with universal healthcare
    #   - Moderate inequality (Gini ~0.29-0.33)
    #   - High union coverage via extension (~90%+ coverage despite low density)
    #   - Declining corporate tax rate (50%→25%)
    #   - High public spending on healthcare and education
    #   - Carbon tax: significant (among European leaders)
    #   - Elite capture low-moderate compared to Anglo-Saxon countries
    #
    # Sources:
    #   [1] OECD Tax Revenue Database, France
    #   [2] WID.world — France Gini series
    #   [3] Piketty (2001, 2014) — France inequality history
    #   [4] INSEE — French National Statistics
    #   [5] ICTWSS — France union data
    #   [6] OECD Health Statistics — France
    #   [7] OECD Education at a Glance — France
    #   [8] Landais, Piketty, Saez (2011) — French tax system
    #   [9] Blanchet & Chancel (2016) — French inequality
    #   [10] World Bank WDI — France Gini
    # ─────────────────────────────────────────────────────────────────────
    'France': {
        'system_label': 'France',

        # Total tax revenue as % of GDP
        # Source: OECD Tax Revenue Database [1]
        # France has among the highest tax burden in OECD.
        'actual_tax_gdp': {
            1960: 32,   # Post-war reconstruction, expanding state
            1980: 41,   # Mitterrand era peak
            2000: 45,   # High-tax equilibrium
            2020: 46,   # Very high (social contributions + income + VAT)
        },
        'actual_tax_gdp_source': 'OECD Tax Revenue Database, France [1]',

        'periods': {
            # ── 1960s: Trente Glorieuses ────────────────────────────────
            # Post-war boom, expanding welfare state
            # Tax system: moderate by modern French standards
            # Inequality: falling from pre-war highs
            # Union power: very strong (close to 30% density)
            # Elite capture: limited by post-war social compact
            1960: {
                'income_tax': 0.25,        # Effective ~25% [1]
                'corp_tax': 0.50,           # ~50% effective [8]
                'welfare': 0.08,            # Expanding social security
                'healthcare': 0.04,         # ~4% GDP [6]
                'education': 0.03,          # ~3% GDP [7]
                'carbon_tax': 0.0,
                'union_premium': 1.15,      # Strong unions
                'cpf': 0.0,
                'elite_capture': 0.08,      # Low-moderate elite power
                'gini_actual': 0.35,        # WID.world [2], Piketty [3]
                # Inequality mechanism keys
                'skill_premium_growth': 0.002,
                'union_coverage': 0.50,          # ~50% coverage (density ~25%) [5]
                'capital_income_share': 0.12,
                'import_competition': 0.10,
                'use_progressive_tax': True,
            },

            # ── 1980s: Mitterrand era ──────────────────────────────────
            # Nationalization wave → later austerity (tournant de la rigueur)
            # High taxes on capital and income
            # Solidarity tax on wealth (ISF) introduced
            # Gini: at historic lows
            # Union coverage: high via extension agreements
            1980: {
                'income_tax': 0.35,        # Effective ~35% [1]
                'corp_tax': 0.50,           # ~50% [8]
                'welfare': 0.15,            # Comprehensive welfare
                'healthcare': 0.07,         # ~7% GDP [6]
                'education': 0.05,          # ~5% GDP [7]
                'carbon_tax': 0.0,
                'union_premium': 1.12,
                'cpf': 0.0,
                'elite_capture': 0.06,      # Low elite capture (wealth tax)
                'gini_actual': 0.30,        # Low point [2][3]
                # Inequality mechanism keys
                'skill_premium_growth': 0.003,
                'union_coverage': 0.85,          # High coverage via extension [5]
                'capital_income_share': 0.10,
                'import_competition': 0.15,
                'use_progressive_tax': True,
            },

            # ── 2000s: European integration ─────────────────────────────
            # Corporate tax falling (competition)
            # 35-hour workweek
            # Gini: very stable (strong redistribution)
            # Welfare state at peak
            2000: {
                'income_tax': 0.38,        # Effective ~38% [1]
                'corp_tax': 0.37,           # Reduced from 50% → ~37% [8]
                'welfare': 0.18,            # Generous welfare state
                'healthcare': 0.10,         # ~10% GDP [6]
                'education': 0.06,          # ~6% GDP [7]
                'carbon_tax': 0.002,        # Early carbon tax (2000) — very low
                'union_premium': 1.10,
                'cpf': 0.0,
                'elite_capture': 0.08,
                'gini_actual': 0.29,        # WID.world [2]
                # Inequality mechanism keys
                'skill_premium_growth': 0.005,
                'union_coverage': 0.90,          # ~90% coverage [5]
                'capital_income_share': 0.15,
                'import_competition': 0.20,
                'use_progressive_tax': True,
            },

            # ── 2020s: Current era ──────────────────────────────────────
            # Macron era: corporate tax cut to 25%, wealth tax reforms
            # Carbon tax raised significantly (€44.6/ton in 2020)
            # Gini: moderate, stable (strong welfare buffers)
            # Union coverage: still high via extension (~95%)
            # Elite capture: rising concern (ISF replaced by IFI)
            2020: {
                'income_tax': 0.45,        # Effective ~45% (income + social contributions) [1]
                'corp_tax': 0.25,           # Reduced to 25% [8]
                'welfare': 0.20,            # High welfare spending
                'healthcare': 0.12,         # ~12.2% GDP [6]
                'education': 0.06,          # ~5.5% GDP [7]
                'carbon_tax': 0.015,        # ~€44.6/t (substantial by intl. standards)
                'union_premium': 1.08,
                'cpf': 0.0,
                'elite_capture': 0.12,      # Rising (wealth tax reform)
                'gini_actual': 0.30,        # WID.world [2], World Bank [10]
                # Inequality mechanism keys
                'skill_premium_growth': 0.006,
                'union_coverage': 0.95,          # Very high via extension [5]
                'capital_income_share': 0.18,
                'import_competition': 0.25,
                'use_progressive_tax': True,
            },
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  Helper Functions
# ═══════════════════════════════════════════════════════════════════════════

def get_period_config(country, period):
    """Get a Phase 8-compatible config dict for a given country and period.

    Returns a flat dict with Phase 8 keys that can be merged into a
    simulation config via ``copy.deepcopy(base_config).update(get_period_config(...))``.

    Example:
        cfg = copy.deepcopy(PHASE8_CONFIGS.get('LS_Full', {}))
        cfg.update(get_period_config('Japan', 2020))
    """
    import copy
    if country not in COUNTRY_DATA:
        raise KeyError(f"Unknown country: {country}.  Choose from {list(COUNTRY_DATA.keys())}")

    country_data = COUNTRY_DATA[country]
    if period not in country_data['periods']:
        raise KeyError(f"Unknown period {period} for {country}.  "
                       f"Available periods: {list(country_data['periods'].keys())}")

    params = country_data['periods'][period]

    # Parameter mapping (same as validate_backtest_historical.py param_map)
    return {
        'income_tax_rate': params['income_tax'],
        'corp_tax_rate': params['corp_tax'],
        'welfare_rate': params['welfare'],
        'healthcare_gdp_share': params.get('healthcare', 0.0),
        'education_gdp_share': params.get('education', 0.0),
        'carbon_tax_rate': params.get('carbon_tax', 0.0),
        'union_premium': params.get('union_premium', 1.0),
        'cpf_rate': params.get('cpf', 0.0),
        'elite_capture_intensity': params.get('elite_capture', 0.0),
        # Inequality mechanism keys
        'skill_premium_growth': params.get('skill_premium_growth', 0.0),
        'union_coverage': params.get('union_coverage', 0.0),
        'capital_income_share': params.get('capital_income_share', 0.0),
        'import_competition': params.get('import_competition', 0.0),
        'use_progressive_tax': params.get('use_progressive_tax', False),
    }


def list_countries():
    """Return list of available country keys."""
    return list(COUNTRY_DATA.keys())


def list_periods(country):
    """Return sorted list of available periods for a given country."""
    if country not in COUNTRY_DATA:
        raise KeyError(f"Unknown country: {country}")
    return sorted(COUNTRY_DATA[country]['periods'].keys())


def print_summary():
    """Print a human-readable summary of all country data."""
    header = (
        f"{'Country':<12} {'Period':<8} {'IncTax':>7} {'CorpTax':>7} "
        f"{'Welfare':>7} {'Health':>7} {'Educ':>7} {'Carbon':>7} "
        f"{'UnionP':>7} {'UnionCov':>7} {'SkillPr':>7} {'CapInc':>7} "
        f"{'Elite':>7} {'Gini':>7}"
    )
    sep = "─" * len(header)
    print(f"\n{'=' * len(header)}")
    print(f"  COUNTRY DATA SUMMARY — Historical Socioeconomic Parameters")
    print(f"{'=' * len(header)}")
    print(header)
    print(sep)

    for country, data in COUNTRY_DATA.items():
        for period in sorted(data['periods']):
            p = data['periods'][period]
            print(
                f"{country:<12} {period:<8} "
                f"{p['income_tax']:>7.3f} {p['corp_tax']:>7.3f} "
                f"{p['welfare']:>7.3f} {p.get('healthcare',0):>7.3f} "
                f"{p.get('education',0):>7.3f} {p.get('carbon_tax',0):>7.3f} "
                f"{p.get('union_premium',1.0):>7.3f} "
                f"{p.get('union_coverage',0):>7.3f} "
                f"{p.get('skill_premium_growth',0):>7.4f} "
                f"{p.get('capital_income_share',0):>7.3f} "
                f"{p.get('elite_capture',0):>7.3f} "
                f"{p['gini_actual']:>7.3f}"
            )
    print(f"{'=' * len(header)}")


def print_tax_gdp():
    """Print tax/GDP ratios for all countries."""
    print(f"\n{'=' * 60}")
    print(f"  Tax Revenue as % of GDP")
    print(f"{'=' * 60}")
    print(f"{'Country':<12} {'1960s':>8} {'1980s':>8} {'2000s':>8} {'2020s':>8}")
    print(f"{'─' * 48}")
    for country, data in COUNTRY_DATA.items():
        tg = data['actual_tax_gdp']
        print(f"{country:<12} {tg.get(1960,0):>7d}% {tg.get(1980,0):>7d}% "
              f"{tg.get(2000,0):>7d}% {tg.get(2020,0):>7d}%")
    print(f"{'=' * 60}")


# ═══════════════════════════════════════════════════════════════════════════
#  Main — display summary when run directly
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print_summary()
    print_tax_gdp()

    print("\n\nData integrity check:")
    for country in COUNTRY_DATA:
        for period in COUNTRY_DATA[country]['periods']:
            p = COUNTRY_DATA[country]['periods'][period]
            # Check required fields
            required = ['income_tax', 'corp_tax', 'welfare', 'gini_actual']
            for field in required:
                assert field in p, f"{country}/{period}: missing {field}"
            # Check ranges
            assert 0 <= p['income_tax'] <= 0.70, f"{country}/{period}: income_tax out of range"
            assert 0 <= p['corp_tax'] <= 0.55, f"{country}/{period}: corp_tax out of range"
            assert 0 <= p['welfare'] <= 0.30, f"{country}/{period}: welfare out of range"
            assert 0 <= p.get('healthcare', 0) <= 0.20, f"{country}/{period}: healthcare out of range"
            assert 0 <= p.get('education', 0) <= 0.10, f"{country}/{period}: education out of range"
            assert 0 <= p.get('carbon_tax', 0) <= 0.05, f"{country}/{period}: carbon_tax out of range"
            assert 0.80 <= p.get('union_premium', 1.0) <= 1.30, f"{country}/{period}: union_premium out of range"
            assert 0 <= p.get('cpf', 0) <= 0.40, f"{country}/{period}: cpf out of range"
            assert 0 <= p.get('elite_capture', 0) <= 0.50, f"{country}/{period}: elite_capture out of range"
            assert 0.20 <= p['gini_actual'] <= 0.65, f"{country}/{period}: gini_actual out of range"
    print("  ✓ All data passes integrity checks.")
