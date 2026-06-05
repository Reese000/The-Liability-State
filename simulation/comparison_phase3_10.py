#!/usr/bin/env python3
"""
comparison_phase3_10.py — Phase 3 comparison runner with 10 economic system models.

Each model integrates adversarial controllers, events, compact competition,
and/or endogenous TFP as appropriate.  Runs 5 seeds × 10 systems × 480 steps.

Systems (all WITH Phase 3 features unless noted):
 1. LS_Full          — LVT 3%, adversarial, pooled insurance, events, compacts, TFP
 2. US_Style         — Income tax 20%, corp tax 21%, adversarial, events, compacts, TFP
 3. Nordic           — Income tax ~35%, welfare 30%, union premium 1.15x
 4. Singapore        — Property tax 5%, CPF 37%, low welfare 10%
 5. Pure_Georgist    — LVT 3% only (NO Phase 3 features)
 6. Mutualist_LS     — LVT 3% + pooled insurance only
 7. Laissez_Faire    — No taxes, no courts, no insurance
 8. Worker_Coop      — LVT + worker co-op profit distribution, wage ratio cap 5x
 9. UBI_VAT          — 20% VAT funding UBI, no other taxes
10. Dual_Compact_LS  — 2 compacts (2% & 4% effective LVT), per-compact tracking
"""

import sys
import os
import json
import time
import logging

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s:%(name)s:%(message)s")

from core.ledger import LedgerEngine, EntityType
from mechanics.courts import CourtSystem, Court, create_case
from mechanics.insurance import InsuranceMarket

from adversarial_bridge import (
    setup_controller,
    choose_agent_strategy,
    adapt_agent_behavior,
)
from insurance_pooling_bridge import (
    setup_pooled_insurance,
    process_claims_pooled,
    get_pooled_premium,
)
from event_injection_bridge import setup_events, apply_event_modifiers
from compact_competition_bridge import (
    create_compacts,
    assign_compact_ids,
    get_compact_lvt_modifier,
    get_compact_litigation_rate,
)

# ─── Constants ───────────────────────────────────────────────────────────
SEEDS = list(range(1, 6))
STEPS = 480
REPORT_INTERVAL = 12
LVT_ANNUAL_RATE = 0.03
LVT_MONTHLY_RATE = LVT_ANNUAL_RATE / 12
HOURS_PER_STEP = 160

INVESTMENT_RATE = 0.3
BUSINESS_WAGE_BILL = 5000.0
WAGE_VARIABILITY = (0.92, 1.0)
ACCIDENT_PROBABILITY = 0.02

TFP_BASELINE = 1.0
TFP_TAX_ELASTICITY = -0.15
LABOR_SUPPLY_ELASTICITY = 0.2

# ─── Population & Ledger Helpers ─────────────────────────────────────────


def make_ledger():
    L = LedgerEngine(step_log=False)
    L.register_entity("sys", EntityType.SYSTEM, initial_cash=500_000_000)
    L.register_entity("trust", EntityType.TRUST)
    L.register_entity("ally", EntityType.ALLIANCE)
    return L


def gen_population(seed):
    rng = np.random.RandomState(seed)
    workers = []
    for i in range(50):
        hourly = rng.uniform(10, 40)
        workers.append(
            {
                "id": f"w{i:03d}",
                "hourly": hourly,
                "monthly": hourly * HOURS_PER_STEP,
                "land": rng.uniform(20000, 200000),
                "risk": rng.uniform(0.01, 0.25),
                "cash": rng.uniform(10000, 80000),
                "honesty": rng.uniform(0.3, 0.95),
                "inertia": rng.uniform(0.05, 0.25),
                "concealment": rng.uniform(0.0, 0.2),
            }
        )
    retirees = []
    for i in range(15):
        retirees.append(
            {
                "id": f"r{seed}_{i:03d}",
                "cash": rng.uniform(80000, 200000),
                "land": rng.uniform(50000, 300000),
            }
        )
    businesses = []
    for i in range(10):
        businesses.append(
            {
                "id": f"b{i:03d}",
                "cash": rng.uniform(100000, 500000),
                "capital": rng.uniform(100000, 400000),
                "tfp": rng.uniform(1.0, 2.0),
                "markup": rng.uniform(1.1, 1.3),
                "honesty": rng.uniform(0.3, 0.9),
            }
        )
    return workers, retirees, businesses


def compute_gini(wealth_list):
    """Compute Gini coefficient from a list of wealth values."""
    if not wealth_list:
        return 0.0
    sw = sorted(wealth_list)
    n = len(sw)
    if n == 0 or sum(sw) == 0:
        return 0.0
    return round(
        (2 * sum((i + 1) * v for i, v in enumerate(sw)) / (n * sum(sw)))
        - (n + 1) / n,
        4,
    )


# ═══════════════════════════════════════════════════════════════════════════
#  Run Phase 3 simulation — extended for all 10 systems
# ═══════════════════════════════════════════════════════════════════════════


def run_phase3(workers, retirees, businesses, seed, config):
    """
    Extended run_phase3 supporting all 10 system types through config-driven
    logic.

    Standard config keys (from existing run_phase3):
        system_name, use_adversarial, use_pooled_insurance, use_events,
        use_compacts, use_endogenous_tfp, tax_type, lvt_rate,
        income_tax_rate, corp_tax_rate

    Extended config keys for model 8 (Worker Co-op):
        use_worker_coop (bool), wage_ratio_cap (int, default 5)

    Extended config keys for model 9 (UBI + VAT):
        use_vat (bool), vat_rate (float, default 0.20)

    Extended config keys for model 10 (Dual Compact):
        use_dual_compact (bool)

    Extended config keys for Nordic / Singapore:
        welfare_rate (float, default 0.15), union_premium (float, default 1.0),
        cpf_rate (float, default 0.0)
    """
    # --- read standard config ---
    name = config.get("system_name", "Phase3")
    use_adversarial = config.get("use_adversarial", False)
    use_pooled = config.get("use_pooled_insurance", False)
    use_events = config.get("use_events", False)
    use_compacts_raw = config.get("use_compacts", False)
    use_endogenous_tfp = config.get("use_endogenous_tfp", False)
    tax_type = config.get("tax_type", "lvt")
    lvt_rate = config.get("lvt_rate", LVT_ANNUAL_RATE)
    income_tax_rate = config.get("income_tax_rate", 0.0)
    corp_tax_rate = config.get("corp_tax_rate", 0.0)

    # --- extended config for new models ---
    use_worker_coop = config.get("use_worker_coop", False)
    wage_ratio_cap = config.get("wage_ratio_cap", 5)
    use_vat = config.get("use_vat", False)
    vat_rate = config.get("vat_rate", 0.20)
    use_dual_compact = config.get("use_dual_compact", False)

    # Nordic / Singapore helpers
    welfare_rate = config.get("welfare_rate", 0.15)
    union_premium = config.get("union_premium", 1.0)
    cpf_rate = config.get("cpf_rate", 0.0)

    # Dual compact uses compacts infrastructure
    use_compacts = use_compacts_raw or use_dual_compact

    _log = logging.getLogger(f'phase3_{name[:20].replace(" ","_")}')

    # ── Setup ledger ───────────────────────────────────────────────────
    ledger = make_ledger()
    rng = np.random.RandomState(seed)
    for w in workers:
        ledger.register_entity(w["id"], EntityType.CITIZEN, initial_cash=w["cash"])
    for r in retirees:
        ledger.register_entity(r["id"], EntityType.CITIZEN, initial_cash=r["cash"])
    for b in businesses:
        ledger.register_entity(
            b["id"], EntityType.BUSINESS, initial_cash=b["cash"]
        )

    # ── Compacts ───────────────────────────────────────────────────────
    if use_compacts:
        compacts, wmap, bmap = create_compacts(
            workers, businesses, n_compacts=2, seed=seed
        )
        assign_compact_ids(workers, businesses, wmap, bmap)
        if use_dual_compact:
            compact_lvt_override = {0: 0.67, 1: 1.33}
            for i, mod in compact_lvt_override.items():
                cid = f"compact_{i}"
                if cid in compacts:
                    compacts[cid]["lvt_modifier"] = mod
    else:
        wmap = {w["id"]: "compact_0" for w in workers}
        bmap = {b["id"]: "compact_0" for b in businesses}
        compacts = {
            "compact_0": {
                "id": "compact_0",
                "name": "Default",
                "court_bias": 0.7,
                "litigation_rate": 0.02,
                "lvt_modifier": 1.0,
            }
        }

    # ── Courts ─────────────────────────────────────────────────────────
    if use_compacts:
        courts = CourtSystem()
        for cid, cdata in compacts.items():
            court_bias = cdata["court_bias"]
            bias_param = (court_bias - 0.5) / 2.0  # 0.5->0.0, 0.9->0.2
            courts.register_court(
                Court(cid, f'{cdata["name"]} Court', 0.03, 5, bias_param, 0.0)
            )
    else:
        courts = CourtSystem()
        courts.register_court(
            Court("fast", "Default Court", 0.03, 5, 0.0, 0.0)
        )

    # ── Insurance ──────────────────────────────────────────────────────
    if use_pooled:
        insurance_policies = setup_pooled_insurance(workers, ledger, loading=1.2)
        mutual_pool = sum(
            p["premium"] for p in insurance_policies.values() if p.get("paid")
        )
    else:
        insurance = InsuranceMarket(
            ledger, base_rate=0.05, loading_factor=1.3
        )
        insurance.register_insurer("ins_a", 500000)
        insurance.register_insurer("ins_b", 400000)
        mutual_pool = 0

    # ── Adversarial controller ─────────────────────────────────────────
    controller = None
    if use_adversarial:
        controller = setup_controller(honesty_mean=0.7)
        agent_strategies = {}

    # ── Events ─────────────────────────────────────────────────────────
    event_manager = None
    shock_step = STEPS // 4
    if use_events:
        event_manager = setup_events(step_shock=shock_step)

    # ── Land values ────────────────────────────────────────────────────
    lvt_monthly_rate = (lvt_rate / 12) if tax_type == "lvt" else 0.0
    wland = {w["id"]: w["land"] for w in workers}
    rland = {r["id"]: r["land"] for r in retirees}
    bland = {b["id"]: rng.uniform(50000, 200000) for b in businesses}

    wid = [w["id"] for w in workers]
    rid = [r["id"] for r in retirees]
    bid = [b["id"] for b in businesses]
    all_citizens = wid + rid
    hist = {"gini": [], "wealth": [], "wmin": [], "wmean": [], "div": [],
            "retiree_gini": [], "retiree_wealth": [], "retiree_mean": []}
    event_log = []

    # Dual-compact per-compact tracking
    compact_wealth_log = {"compact_0": [], "compact_1": []}
    compact_gini_log = {"compact_0": [], "compact_1": []}

    # Worker co-op reference minimum wage
    base_min_wage = min(w["monthly"] for w in workers)

    # ── Main simulation loop ───────────────────────────────────────────
    for step in range(1, STEPS + 1):
        try:
            ledger.begin_step()

            # -- 0. Event injection -------------------------------------
            demand_mult = 1.0
            claim_freq_mult = 1.0
            if event_manager:
                logs = event_manager.fire_events(
                    {
                        "workers": workers,
                        "businesses": businesses,
                        "ledger": ledger,
                        "courts": courts,
                    },
                    step,
                )
                event_log.extend(logs)
                mods = event_manager.get_active_modifiers(step)
                if "demand_multiplier" in mods:
                    demand_mult = mods["demand_multiplier"]
                if "claim_freq_multiplier" in mods:
                    claim_freq_mult = mods["claim_freq_multiplier"]
                if "land_value_multiplier" in mods:
                    for w in workers:
                        wland[w["id"]] *= mods["land_value_multiplier"]
                    for r in retirees:
                        rland[r["id"]] *= mods["land_value_multiplier"]
                    for b in businesses:
                        bland[b["id"]] *= mods["land_value_multiplier"]

            # -- 1. Wages -----------------------------------------------
            step_wages = {}
            for w in workers:
                # Labor supply response: workers choose hours based on after-tax wage
                pre_tax_wage = w["hourly"]
                if tax_type == "income":
                    after_tax_wage = pre_tax_wage * (1 - income_tax_rate)
                else:
                    # LVT, none, or VAT systems don't tax labor directly
                    after_tax_wage = pre_tax_wage
                # hours = baseline_hours * (after_tax_wage / pre_tax_wage)^δ
                labor_supply_ratio = (
                    (after_tax_wage / pre_tax_wage) ** LABOR_SUPPLY_ELASTICITY
                    if pre_tax_wage > 0 else 1.0
                )
                inc = w["monthly"] * labor_supply_ratio * rng.uniform(*WAGE_VARIABILITY)
                inc *= union_premium  # Nordic union premium
                if inc > 0:
                    if use_endogenous_tfp:
                        if tax_type == "income" and income_tax_rate > 0:
                            effective_tax = income_tax_rate
                        elif tax_type == "lvt":
                            annual_lvt = wland[w["id"]] * lvt_rate
                            effective_tax = min(
                                0.5, annual_lvt / max(w["monthly"] * 12, 1)
                            )
                        else:
                            effective_tax = 0.0
                        tfp_factor = max(
                            0.5, 1.0 + TFP_TAX_ELASTICITY * effective_tax
                        )
                        inc *= tfp_factor
                    ledger.transfer("sys", w["id"], "wage", inc)
                    step_wages[w["id"]] = inc

            # -- 2. Business activity -----------------------------------
            for b in businesses:
                try:
                    tfp_val = b["tfp"]
                    rev = (
                        tfp_val
                        * (b["capital"] ** 0.3)
                        * (8 ** 0.7)
                        * b["markup"]
                        * demand_mult
                    )

                    adv_markup = 1.0
                    if controller and b["id"] in agent_strategies:
                        astrat = agent_strategies[b["id"]]
                        if astrat == "Collusion":
                            adv_markup = 1.15

                    rev *= adv_markup
                    profit = rev - BUSINESS_WAGE_BILL

                    if profit > 0:
                        tax_amount = 0.0
                        if tax_type == "income" and corp_tax_rate > 0:
                            tax_amount = profit * corp_tax_rate

                        after_tax = profit - tax_amount

                        if tax_amount > 0:
                            ledger.transfer(
                                b["id"], "sys", "corp_tax", tax_amount
                            )

                        if use_worker_coop:
                            # ── Worker Co-op profit distribution ──────
                            # All after-tax profit goes to workers as
                            # cooperative dividend (proportional to wages)
                            # after reserving investment.
                            ledger.transfer(
                                "sys", b["id"], "rev", after_tax
                            )
                            inv = after_tax * INVESTMENT_RATE
                            if inv > 0:
                                ledger.transfer(
                                    b["id"], "sys", "invest", inv
                                )
                                b["capital"] += inv

                            coop_pool = after_tax - inv
                            if coop_pool > 0.01 and step_wages:
                                total_wages = sum(step_wages.values())
                                if total_wages > 0:
                                    max_total = (
                                        base_min_wage * wage_ratio_cap
                                    )
                                    for w in workers:
                                        wid_ = w["id"]
                                        wage = step_wages.get(wid_, 0)
                                        prop_share = coop_pool * (
                                            wage / total_wages
                                        )
                                        cap_room = max(
                                            0, max_total - wage
                                        )
                                        actual = min(
                                            prop_share, cap_room
                                        )
                                        if actual > 0.01:
                                            ledger.transfer(
                                                b["id"],
                                                wid_,
                                                "coop_dividend",
                                                actual,
                                            )
                        else:
                            # ── Standard profit distribution ──────────
                            ledger.transfer(
                                "sys", b["id"], "rev", after_tax
                            )
                            inv = after_tax * INVESTMENT_RATE
                            if inv > 0:
                                ledger.transfer(
                                    b["id"], "sys", "invest", inv
                                )
                                b["capital"] += inv
                except Exception as e:
                    _log.warning(
                        "Step %d biz %s: %s", step, b["id"], e
                    )

            # -- 3. Insurance -------------------------------------------
            if use_pooled:
                claim_prob = 0.3 * claim_freq_mult
                mutual_pool, _ = process_claims_pooled(
                    workers,
                    ledger,
                    mutual_pool,
                    rng,
                    step,
                    claim_prob_mult=claim_prob,
                )
            else:
                for w in workers:
                    try:
                        p = insurance.price_policy(
                            w["id"], w["risk"], 50000
                        )
                        if (
                            p
                            < ledger.balances[w["id"]].cash * 0.1
                        ):
                            insurance.purchase_policy(
                                w["id"], "ins_a", w["risk"], 50000
                            )
                    except Exception:
                        pass
                insurance.run_step()

            # -- 4. Adversarial strategy evaluation ----------------------
            if controller:
                for w in workers:
                    strat, ev, det = choose_agent_strategy(
                        controller, w, ledger, step, rng
                    )
                    if strat:
                        agent_strategies[w["id"]] = strat
                        mods = adapt_agent_behavior(
                            w, strat, ledger, step, rng
                        )
                        if "declared_risk" in mods:
                            w["risk"] = mods["declared_risk"]
                for b in businesses:
                    strat, ev, det = choose_agent_strategy(
                        controller, b, ledger, step, rng
                    )
                    if strat:
                        agent_strategies[b["id"]] = strat

            # -- 5. Tax collection --------------------------------------
            if use_vat:
                # ── VAT on wages (replaces all other taxes) ──────────
                total_vat = 0.0
                if hasattr(ledger, "step"):
                    for w in workers:
                        try:
                            step_transfers = [
                                t
                                for t in ledger.transfers
                                if getattr(t, "step", 0) == step
                                and getattr(t, "mechanism", "") == "wage"
                                and getattr(t, "entity_id", "") == w["id"]
                            ]
                            for t in step_transfers:
                                vat = t.amount * vat_rate
                                if vat > 0:
                                    try:
                                        ledger.transfer(
                                            w["id"], "sys", "vat", vat
                                        )
                                        total_vat += vat
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                # ── UBI distribution (flat, equal to all citizens) ───────
                ubi_per_person = (
                    total_vat / len(all_citizens)
                    if total_vat > 0 and all_citizens
                    else 0
                )
                if ubi_per_person > 0:
                    for c_id in all_citizens:
                        try:
                            ledger.transfer(
                                "sys", c_id, "ubi", ubi_per_person
                            )
                        except Exception:
                            pass

            elif tax_type == "lvt":
                # LVT on workers
                for w in workers:
                    try:
                        cid = wmap.get(w["id"], "compact_0")
                        lvt_mod = (
                            get_compact_lvt_modifier(cid, compacts)
                            if use_compacts
                            else 1.0
                        )
                        effective_monthly = lvt_monthly_rate * lvt_mod
                        d = wland[w["id"]] * effective_monthly
                        if ledger.balances[w["id"]].cash >= d:
                            ledger.transfer(
                                w["id"], "trust", "lvt", d
                            )
                    except Exception as e:
                        _log.warning(
                            "Step %d LVT w %s: %s", step, w["id"], e
                        )
                # LVT on retirees
                for r in retirees:
                    try:
                        d = rland[r["id"]] * lvt_monthly_rate
                        if ledger.balances[r["id"]].cash >= d:
                            ledger.transfer(
                                r["id"], "trust", "lvt", d
                            )
                    except Exception as e:
                        _log.warning(
                            "Step %d LVT r %s: %s", step, r["id"], e
                        )
                for b in businesses:
                    try:
                        cid = bmap.get(b["id"], "compact_0")
                        lvt_mod = (
                            get_compact_lvt_modifier(cid, compacts)
                            if use_compacts
                            else 1.0
                        )
                        effective_monthly = lvt_monthly_rate * lvt_mod
                        d = bland[b["id"]] * effective_monthly
                        if ledger.balances[b["id"]].cash >= d:
                            ledger.transfer(
                                b["id"], "trust", "lvt", d
                            )
                    except Exception as e:
                        _log.warning(
                            "Step %d LVT b %s: %s", step, b["id"], e
                        )

            elif tax_type == "income":
                # Income tax on wages
                for w in workers:
                    try:
                        if hasattr(ledger, "step"):
                            step_transfers = [
                                t
                                for t in ledger.transfers
                                if getattr(t, "step", 0) == step
                                and getattr(t, "mechanism", "") == "wage"
                                and getattr(t, "entity_id", "") == w["id"]
                            ]
                            for t in step_transfers:
                                wage_amt = t.amount
                                tax = wage_amt * income_tax_rate
                                if tax > 0:
                                    try:
                                        ledger.transfer(
                                            w["id"],
                                            "sys",
                                            "income_tax",
                                            tax,
                                        )
                                    except Exception:
                                        pass
                    except Exception:
                        pass

                # CPF collection (Singapore: forced savings)
                if cpf_rate > 0:
                    for w in workers:
                        wage = step_wages.get(w["id"], 0)
                        cpf = wage * cpf_rate
                        if cpf > 0:
                            try:
                                ledger.transfer(
                                    w["id"], "sys", "cpf", cpf
                                )
                            except Exception:
                                pass

            # tax_type == 'none' → skip all tax collection

            # -- 6. Dividend (if LVT) ------------------------------------
            if tax_type == "lvt":
                tl = sum(
                    t.amount
                    for t in ledger.transfers
                    if getattr(t, "step", 0) == step
                    and getattr(t, "mechanism", "") == "lvt"
                )
                pc = tl * 0.90 / len(all_citizens) if tl > 0 else 0
                if tl * 0.10 > 0:
                    try:
                        ledger.transfer("trust", "ally", "skim", tl * 0.10)
                    except Exception:
                        pass
                for c_id in all_citizens:
                    if pc > 0:
                        try:
                            ledger.transfer(
                                "trust", c_id, "dividend", pc
                            )
                        except Exception:
                            pass
            else:
                pc = 0.0

            # -- 7. Courts ----------------------------------------------
            for b in businesses:
                try:
                    cid = bmap.get(b["id"], "compact_0")
                    lit_rate = (
                        get_compact_litigation_rate(cid, compacts)
                        if use_compacts
                        else ACCIDENT_PROBABILITY
                    )
                except Exception:
                    lit_rate = ACCIDENT_PROBABILITY

                if rng.random() < lit_rate:
                    try:
                        pl = rng.choice(wid)
                        amt = rng.uniform(1000, 20000)
                        c = create_case(
                            pl,
                            b["id"],
                            amt,
                            rng.uniform(0.3, 0.8),
                            0.1,
                        )
                        courts.route_case(c, step=step)
                    except Exception:
                        pass
            courts.tick(step)

            # -- 8. Welfare (if income tax system) ----------------------
            if tax_type == "income" and income_tax_rate > 0:
                total_tax = sum(
                    t.amount
                    for t in ledger.transfers
                    if getattr(t, "step", 0) == step
                    and getattr(t, "mechanism", "") == "income_tax"
                )
                welfare_amt = total_tax * welfare_rate
                if welfare_amt > 0:
                    per_w = welfare_amt / len(all_citizens)
                    for c_id in all_citizens:
                        try:
                            ledger.transfer(
                                "sys", c_id, "welfare", per_w
                            )
                        except Exception:
                            pass

            # -- 9. CPF redistribution (return forced savings) ----------
            if cpf_rate > 0:
                total_cpf = sum(
                    t.amount
                    for t in ledger.transfers
                    if getattr(t, "step", 0) == step
                    and getattr(t, "mechanism", "") == "cpf"
                )
                if total_cpf > 0:
                    per_cpf = total_cpf / len(wid)
                    for w_id in wid:
                        try:
                            ledger.transfer(
                                "sys", w_id, "cpf_return", per_cpf
                            )
                        except Exception:
                            pass

            ledger.close_step()

        except Exception as e:
            _log.error("Fatal at step %d: %s", step, e)
            try:
                ledger.close_step()
            except Exception:
                pass
            break

        # -- Report -----------------------------------------------------
        if step % REPORT_INTERVAL == 0:
            ww = [
                ledger.balances[i].cash
                for i in wid
                if i in ledger.balances
            ]
            if ww:
                sw = sorted(ww)
                n = len(sw)
                g = (
                    (
                        2
                        * sum((i + 1) * v for i, v in enumerate(sw))
                        / (n * sum(sw))
                    )
                    - (n + 1) / n
                    if n and sum(sw)
                    else 0
                )
                hist["gini"].append(round(g, 4))
                hist["wealth"].append(
                    sum(b.cash for b in ledger.balances.values())
                )
                hist["wmin"].append(min(ww))
                hist["wmean"].append(np.mean(ww))
                hist["div"].append(pc)

            # Retiree stats
            rw = [
                ledger.balances[i].cash
                for i in rid
                if i in ledger.balances
            ]
            if rw:
                hist["retiree_gini"].append(compute_gini(rw))
                hist["retiree_wealth"].append(sum(rw))
                hist["retiree_mean"].append(np.mean(rw))

            # Dual compact per-compact tracking
            if use_dual_compact:
                for cid in ["compact_0", "compact_1"]:
                    c_wealth = [
                        ledger.balances[w["id"]].cash
                        for w in workers
                        if w.get("compact_id") == cid
                        and w["id"] in ledger.balances
                    ]
                    if c_wealth:
                        compact_wealth_log[cid].append(sum(c_wealth))
                        compact_gini_log[cid].append(
                            compute_gini(c_wealth)
                        )

    # ── Final metrics ─────────────────────────────────────────────────
    ww = [ledger.balances[i].cash for i in wid if i in ledger.balances]
    if ww:
        sw = sorted(ww)
        n = len(sw)
        g = (
            (
                2
                * sum((i + 1) * v for i, v in enumerate(sw))
                / (n * sum(sw))
            )
            - (n + 1) / n
            if n and sum(sw)
            else 0
        )
    else:
        g = 0.0

    # Retiree final metrics
    rw = [ledger.balances[i].cash for i in rid if i in ledger.balances]
    retiree_gini = compute_gini(rw) if rw else 0.0
    retiree_mean = round(np.mean(rw), 2) if rw else 0

    result = {
        "name": name,
        "wealth": sum(b.cash for b in ledger.balances.values()),
        "gini": round(g, 4),
        "w_mean": round(np.mean(ww), 2) if ww else 0,
        "w_min": round(min(ww), 2) if ww else 0,
        "w_max": round(max(ww), 2) if ww else 0,
        "div": round(pc, 2),
        "retiree_gini": round(retiree_gini, 4),
        "retiree_mean": retiree_mean,
        "retiree_wealth": round(sum(rw), 2) if rw else 0,
        "txns": len(ledger.transfers),
        "steps": STEPS,
        "config": {
            k: v
            for k, v in config.items()
            if isinstance(v, (str, int, float, bool))
        },
    }

    # Include per-compact metrics for dual compact
    if use_dual_compact:
        result["compact_wealth"] = {
            cid: compact_wealth_log[cid] for cid in ["compact_0", "compact_1"]
        }
        result["compact_gini"] = {
            cid: compact_gini_log[cid] for cid in ["compact_0", "compact_1"]
        }
        # Final per-compact stats
        for cid in ["compact_0", "compact_1"]:
            c_wealth = [
                ledger.balances[w["id"]].cash
                for w in workers
                if w.get("compact_id") == cid
                and w["id"] in ledger.balances
            ]
            if c_wealth:
                result[f"w_mean_{cid}"] = round(
                    np.mean(c_wealth), 2
                )
                result[f"gini_{cid}"] = compute_gini(c_wealth)

    return result


# ═══════════════════════════════════════════════════════════════════════════
#  Experiment configurations
# ═══════════════════════════════════════════════════════════════════════════


def build_experiments():
    """Return a list of 10 config dicts, one per system/scenario."""

    def _base_ls_full():
        return {
            "use_adversarial": True,
            "use_pooled_insurance": True,
            "use_events": True,
            "use_compacts": True,
            "use_endogenous_tfp": True,
            "tax_type": "lvt",
            "lvt_rate": 0.03,
            "income_tax_rate": 0.0,
            "corp_tax_rate": 0.0,
        }

    exps = []

    # 1. LS_Full — LVT 3%, all Phase 3 features active
    cfg = _base_ls_full()
    cfg["system_name"] = "LS_Full"
    exps.append(cfg)

    # 2. US_Style — Income tax 20%, corp tax 21%
    exps.append(
        {
            "system_name": "US_Style",
            "use_adversarial": True,
            "use_pooled_insurance": False,
            "use_events": True,
            "use_compacts": True,
            "use_endogenous_tfp": True,
            "tax_type": "income",
            "income_tax_rate": 0.20,
            "corp_tax_rate": 0.21,
        }
    )

    # 3. Nordic — Income tax ~35%, welfare 30%, union premium 1.15
    exps.append(
        {
            "system_name": "Nordic",
            "use_adversarial": True,
            "use_pooled_insurance": False,
            "use_events": True,
            "use_compacts": True,
            "use_endogenous_tfp": True,
            "tax_type": "income",
            "income_tax_rate": 0.35,
            "corp_tax_rate": 0.21,
            "welfare_rate": 0.30,
            "union_premium": 1.15,
        }
    )

    # 4. Singapore — Property tax 5%, CPF 37%, low welfare 10%
    exps.append(
        {
            "system_name": "Singapore",
            "use_adversarial": True,
            "use_pooled_insurance": False,
            "use_events": True,
            "use_compacts": True,
            "use_endogenous_tfp": True,
            "tax_type": "income",
            "income_tax_rate": 0.05,
            "corp_tax_rate": 0.17,
            "cpf_rate": 0.37,
            "welfare_rate": 0.10,
        }
    )

    # 5. Pure_Georgist — LVT 3%, NO Phase 3 features
    exps.append(
        {
            "system_name": "Pure_Georgist",
            "use_adversarial": False,
            "use_pooled_insurance": False,
            "use_events": False,
            "use_compacts": False,
            "use_endogenous_tfp": False,
            "tax_type": "lvt",
            "lvt_rate": 0.03,
            "income_tax_rate": 0.0,
            "corp_tax_rate": 0.0,
        }
    )

    # 6. Mutualist_LS — LVT + pooled insurance only (no adversarial/events/compacts/TFP)
    exps.append(
        {
            "system_name": "Mutualist_LS",
            "use_adversarial": False,
            "use_pooled_insurance": True,
            "use_events": False,
            "use_compacts": False,
            "use_endogenous_tfp": False,
            "tax_type": "lvt",
            "lvt_rate": 0.03,
            "income_tax_rate": 0.0,
            "corp_tax_rate": 0.0,
        }
    )

    # 7. Laissez_Faire — No taxes, no insurance, minimal courts
    exps.append(
        {
            "system_name": "Laissez_Faire",
            "use_adversarial": False,
            "use_pooled_insurance": False,
            "use_events": False,
            "use_compacts": False,
            "use_endogenous_tfp": False,
            "tax_type": "none",
            "lvt_rate": 0.0,
            "income_tax_rate": 0.0,
            "corp_tax_rate": 0.0,
        }
    )

    # 8. Worker_Coop — LVT + worker co-op profit distribution
    cfg = _base_ls_full()
    cfg["system_name"] = "Worker_Coop"
    cfg["use_worker_coop"] = True
    cfg["wage_ratio_cap"] = 5
    exps.append(cfg)

    # 9. UBI_VAT — 20% VAT funding universal basic income
    exps.append(
        {
            "system_name": "UBI_VAT",
            "use_adversarial": True,
            "use_pooled_insurance": True,
            "use_events": True,
            "use_compacts": True,
            "use_endogenous_tfp": True,
            "tax_type": "none",
            "lvt_rate": 0.0,
            "income_tax_rate": 0.0,
            "corp_tax_rate": 0.0,
            "use_vat": True,
            "vat_rate": 0.20,
        }
    )

    # 10. Dual_Compact_LS — LS Full with 2% / 4% effective LVT compacts
    cfg = _base_ls_full()
    cfg["system_name"] = "Dual_Compact_LS"
    cfg["use_dual_compact"] = True
    exps.append(cfg)

    return exps


# ═══════════════════════════════════════════════════════════════════════════
#  Runner
# ═══════════════════════════════════════════════════════════════════════════


def run_batch(seeds, experiments):
    results = {e["system_name"]: [] for e in experiments}
    total = len(seeds) * len(experiments)
    t0 = time.time()

    for exp in experiments:
        name = exp["system_name"]
        print(f"\n{'='*60}")
        print(f"  {name}")
        print(f"{'='*60}")

        for seed in seeds:
            pop = gen_population(seed)
            r = run_phase3(*pop, seed, exp)
            results[name].append(r)
            print(
                f"  seed {seed:3d}: Gini={r['gini']:.4f}  "
                f"Mean=${r['w_mean']:>9,.0f}  "
                f"Div=${r['div']:>6.2f}  Steps={r['steps']}"
            )
            if "retiree_mean" in r and r["retiree_mean"]:
                print(
                    f"           Retiree Gini={r['retiree_gini']:.4f}  "
                    f"Retiree Mean=${r['retiree_mean']:>9,.0f}"
                )
            # Print dual-compact per-compact stats if present
            if "gini_compact_0" in r:
                print(
                    f"            compact_0 Gini={r['gini_compact_0']:.4f}  "
                    f"Mean=${r['w_mean_compact_0']:>9,.0f}  |  "
                    f"compact_1 Gini={r['gini_compact_1']:.4f}  "
                    f"Mean=${r['w_mean_compact_1']:>9,.0f}"
                )

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    return results


def summarize(results):
    print(f"\n{'='*120}")
    print("  PHASE 3 COMPARISON — 10 SYSTEMS")
    print("=" * 120)

    header = (
        f"{'System':<28} {'Mean Wealth':>12} {'Min Wealth':>12} "
        f"{'Max Wealth':>12} {'Gini Mean':>10} {'Gini SD':>9} "
        f"{'Dividend':>10} {'Steps':>8}"
    )
    print(header)
    print("-" * 120)

    for sys_name in results:
        runs = results[sys_name]
        w_means = [r["w_mean"] for r in runs]
        w_mins = [r["w_min"] for r in runs]
        w_maxs = [r["w_max"] for r in runs]
        ginis = [r["gini"] for r in runs]
        divs = [r["div"] for r in runs]
        steps = runs[0]["steps"] if runs else 0

        print(
            f"{sys_name:<28} "
            f"${np.mean(w_means):>10,.0f} ± ${np.std(w_means):>7,.0f} "
            f"${np.mean(w_mins):>10,.0f} "
            f"${np.mean(w_maxs):>10,.0f} "
            f"{np.mean(ginis):>8.4f}  ±{np.std(ginis):>6.4f} "
            f"${np.mean(divs):>7.2f} "
            f"{steps:>8}"
        )

    # Retiree summary table
    print(f"\n{'='*80}")
    print("  RETIREE METRICS")
    print("=" * 80)
    retiree_header = (
        f"{'System':<28} {'Retiree Mean':>14} {'Retiree Gini':>14}"
    )
    print(retiree_header)
    print("-" * 80)
    for sys_name in results:
        runs = results[sys_name]
        r_means = [r.get("retiree_mean", 0) for r in runs]
        r_ginis = [r.get("retiree_gini", 0) for r in runs]
        if r_means and any(r_means):
            print(
                f"{sys_name:<28} "
                f"${np.mean(r_means):>10,.0f}  ±${np.std(r_means):>7,.0f} "
                f"{np.mean(r_ginis):>12.4f}"
            )

    # Ranking by mean worker wealth
    print(f"\n{'Rank by Mean Worker Wealth':^80}")
    print("-" * 80)
    ranked = sorted(
        [
            (np.mean([r["w_mean"] for r in results[sn]]), sn)
            for sn in results
        ],
        reverse=True,
    )
    for i, (val, name) in enumerate(ranked, 1):
        print(f"  {i}. {name:<30} ${val:>10,.0f}")

    print(f"\n{'Rank by Lowest Inequality (Gini)':^80}")
    print("-" * 80)
    ranked = sorted(
        [
            (np.mean([r["gini"] for r in results[sn]]), sn)
            for sn in results
        ]
    )
    for i, (val, name) in enumerate(ranked, 1):
        print(f"  {i}. {name:<30} {val:.4f}")

    # Dual-Compact per-compact summary
    has_dual = any(
        "compact_wealth" in r
        for runs in results.values()
        for r in runs
    )
    if has_dual:
        print(f"\n{'Dual Compact — Per-Compact Metrics':^80}")
        print("-" * 80)
        dual_name = "Dual_Compact_LS"
        if dual_name in results:
            for cid in ["compact_0", "compact_1"]:
                c_w_means = [
                    r.get(f"w_mean_{cid}", 0)
                    for r in results[dual_name]
                ]
                c_ginis = [
                    r.get(f"gini_{cid}", 0)
                    for r in results[dual_name]
                ]
                if c_w_means:
                    print(
                        f"  {cid:<20} "
                        f"Mean Wealth: ${np.mean(c_w_means):>9,.0f}  "
                        f"Gini: {np.mean(c_ginis):.4f}"
                    )


# ═══════════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    seeds = SEEDS
    if "--quick" in sys.argv:
        seeds = list(range(1, 3))

    experiments = build_experiments()
    n_sims = len(seeds) * len(experiments)
    print(
        f"Running {len(seeds)} seeds × {len(experiments)} experiments"
        f" = {n_sims} simulations"
    )
    print(
        f"Each: {STEPS} steps (40 years) with 50 workers, "
        f"15 retirees, 10 businesses"
    )

    results = run_batch(seeds, experiments)
    summarize(results)

    # Save
    os.makedirs("output", exist_ok=True)
    out_path = "output/phase3_10_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")
