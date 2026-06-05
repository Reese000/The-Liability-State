"""
agents/business.py — BusinessAgent

Each business has: capital, workers hired, production function (Cobb-Douglas),
product price, liability exposure, insurance.

Per-step decision loop:
  1. Decide hiring — marginal product of labour vs market wage
  2. Set product price — cost-plus markup
  3. Produce & sell — revenue via ledger
  4. Pay wages — wage bill via ledger
  5. Buy liability insurance — premium via ledger
  6. Face accident risk — stochastic liability events
  7. Invest in expansion — reinvest profits into capital stock

All monetary flows go through the LedgerEngine (double-entry accounting).
Designed to match AGENT_MODEL.md §2.2, §3.3, §9.2.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

try:
    from ..core.ledger import LedgerEngine, EntityType
except (ImportError, ValueError):
    try:
        from core.ledger import LedgerEngine, EntityType
    except ModuleNotFoundError:
        # Fallback for standalone execution: add src/ to sys.path
        import sys, os
        _src_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
        if _src_dir not in sys.path:
            sys.path.insert(0, _src_dir)
        from core.ledger import LedgerEngine, EntityType


# ══════════════════════════════════════════════════════════════════════
#  Business Agent
# ══════════════════════════════════════════════════════════════════════

class BusinessAgent:
    """
    A productive enterprise that hires workers, produces goods,
    sets prices, buys insurance, and faces accident liability risk.

    Production uses a Cobb-Douglas function:
        Q = TFP * K^α * L^(1-α)

    Where:
      - K = capital stock
      - L = number of workers
      - α = capital share (default 0.30)
      - TFP = total factor productivity

    All financial flows are recorded on the LedgerEngine.
    """

    # ── Default Parameters ──────────────────────────────────────

    # Cobb-Douglas shares (must sum to ~1.0)
    DEFAULT_CAPITAL_SHARE = 0.30
    DEFAULT_LABOR_SHARE = 0.70
    DEFAULT_TFP = 1.0

    # Pricing
    DEFAULT_MARKUP = 1.20               # price = unit_cost * markup

    # Safety / insurance
    DEFAULT_SAFETY_INVESTMENT_RATE = 0.05  # fraction of revenue
    DEFAULT_COVERAGE_TARGET = 0.80         # target fraction of exposure insured

    # Investment
    DEFAULT_REINVESTMENT_RATE = 0.30       # fraction of after-tax profit

    # Employment friction
    MAX_WORKERS = 100                      # hard cap on workforce

    # ── Constructor ─────────────────────────────────────────────

    def __init__(
        self,
        agent_id: str,
        ledger: LedgerEngine,
        *,
        # Initial balance sheet
        initial_cash: float = 100_000.0,
        initial_capital: float = 100_000.0,

        # Production parameters
        tfp: Optional[float] = None,
        capital_share: Optional[float] = None,

        # Risk
        liability_exposure: float = 0.05,       # base accident probability per step

        # Market context (observed each step, but we store defaults)
        market_wage: float = 15.0,
        market_price: float = 10.0,
        markup: Optional[float] = None,
        reinvestment_rate: Optional[float] = None,

        # ── Lifecycle
        tick_created: int = 0,
    ):
        self.id = agent_id
        self.ledger = ledger
        self.tick_created = tick_created
        self.alive = True
        self._consecutive_negative_steps = 0  # business bankruptcy counter

        # ── Register with ledger ─────────────────────────────────
        if not ledger.entity_exists(agent_id):
            ledger.register_entity(
                agent_id,
                EntityType.BUSINESS,
                initial_cash=initial_cash,
            )

        # ── Balance sheet ────────────────────────────────────────
        self.capital = initial_capital            # Capital stock K
        self.workers_hired: list[str] = []        # Employed worker IDs
        self.insurance_policy: Optional[dict] = None  # {insurer_id, premium, coverage_limit, ...}

        # ── Production function ──────────────────────────────────
        self.tfp = tfp if tfp is not None else self.DEFAULT_TFP
        self.capital_share = (
            capital_share if capital_share is not None
            else self.DEFAULT_CAPITAL_SHARE
        )
        self._labor_share = 1.0 - self.capital_share  # derived

        # ── Pricing ──────────────────────────────────────────────
        self.price = market_price
        self.markup = markup if markup is not None else self.DEFAULT_MARKUP

        # ── Risk & insurance ─────────────────────────────────────
        self.liability_exposure = max(0.0, min(1.0, liability_exposure))
        self.safety_investment_rate = self.DEFAULT_SAFETY_INVESTMENT_RATE
        self._effective_exposure = self.liability_exposure  # updated by safety investment

        # ── Investment ───────────────────────────────────────────
        self.reinvestment_rate = (
            reinvestment_rate if reinvestment_rate is not None
            else self.DEFAULT_REINVESTMENT_RATE
        )

        # ── Market context (updated each step) ───────────────────
        self.market_wage = market_wage
        self.market_demand_factor = 1.0  # scalar applied to sales

        # ── Period accounting ────────────────────────────────────
        self.reset_period_accounting()

    # ── Property helpers ─────────────────────────────────────────

    @property
    def labor_count(self) -> int:
        """Number of currently employed workers."""
        return len(self.workers_hired)

    @property
    def cash(self) -> float:
        """Current cash balance from ledger."""
        try:
            return self.ledger.get_balance(self.id).cash
        except KeyError:
            return 0.0

    @property
    def net_worth(self) -> float:
        """Net worth = cash + capital - outstanding liabilities."""
        try:
            bs = self.ledger.get_balance(self.id)
            return bs.cash + self.capital - bs.outstanding_liability
        except KeyError:
            return self.capital

    # ══════════════════════════════════════════════════════════════
    #  Production Function
    # ══════════════════════════════════════════════════════════════

    def production_function(self, labor: int) -> float:
        """
        Cobb-Douglas output:  Q = TFP * K^α * L^(1-α)

        Returns physical output units for the given labour count.
        """
        if labor <= 0 or self.capital <= 0:
            return 0.0
        # Use float exponents to handle fractional labour gracefully
        return (
            self.tfp
            * (self.capital ** self.capital_share)
            * (float(labor) ** self._labor_share)
        )

    def marginal_product_of_labor(self, labor: int) -> float:
        """
        MPL = ∂Q/∂L = (1-α) * TFP * K^α * L^(-α)

        For L=0, returns the MPL at L=1 as an approximation.
        """
        if labor <= 0:
            return self.production_function(1)
        return self._labor_share * self.production_function(labor) / float(labor)

    def unit_cost(self) -> float:
        """
        Average unit cost = (wage_bill + capital_charge) / Q.

        Returns an estimate of cost per unit of output.
        """
        q = self.production_function(max(self.labor_count, 1))
        if q <= 0:
            return float('inf')
        wage_bill = self.market_wage * max(self.labor_count, 1)
        # Approximate capital cost as 5% opportunity cost
        capital_charge = self.capital * 0.05
        return (wage_bill + capital_charge) / q

    # ══════════════════════════════════════════════════════════════
    #  Decision Methods  (called by step())
    # ══════════════════════════════════════════════════════════════

    def decide_hiring(self) -> int:
        """
        Hire/fire workers so that MPL ≈ market_wage.

        - If MPL > wage: profitable to hire more → expand workforce.
        - If MPL < wage * 0.8: overstaffed → lay off workers.
        - Otherwise: hold steady.

        Returns the net change in worker count.
        """
        current_l = self.labor_count
        if current_l >= self.MAX_WORKERS:
            return 0

        target_l = current_l

        if current_l == 0:
            # Check if first worker is viable
            if self.marginal_product_of_labor(1) >= self.market_wage:
                target_l = 1
            else:
                return 0
        else:
            mpl = self.marginal_product_of_labor(current_l)
            if mpl > self.market_wage:
                # Understaffed — find optimal L
                test_l = current_l
                while test_l < self.MAX_WORKERS:
                    test_l += 1
                    if self.marginal_product_of_labor(test_l) < self.market_wage:
                        break
                target_l = test_l - 1  # last L where MPL >= wage
            elif mpl < self.market_wage * 0.8:
                # Overstaffed — reduce
                test_l = current_l
                while test_l > 0:
                    test_l -= 1
                    if (self.marginal_product_of_labor(max(test_l, 1))
                            >= self.market_wage):
                        break
                target_l = test_l

        target_l = max(0, min(target_l, self.MAX_WORKERS))
        net = target_l - current_l

        # Apply workforce change
        if net > 0:
            for i in range(net):
                wid = f"{self.id}_w_{len(self.workers_hired)}"
                self.workers_hired.append(wid)
        elif net < 0:
            # Remove from the end
            self.workers_hired = self.workers_hired[:net]  # net is negative

        return net

    def decide_price(self):
        """
        Set product price based on cost-plus markup.

        price = unit_cost * markup
        Also clamped by a sanity range.
        """
        uc = self.unit_cost()
        if math.isfinite(uc) and uc > 0:
            new_price = uc * self.markup
        else:
            new_price = self.price  # keep previous

        # Clamp to reasonable range
        new_price = max(1.0, min(new_price, 1_000.0))
        self.price = new_price

    def decide_safety_investment(self):
        """
        Adjust safety investment and update effective liability exposure.

        Higher safety investment reduces accident probability but costs money.
        Effective exposure = base_exposure * (1 - safety_investment).
        """
        # Safety investment already set as rate; compute effective exposure
        self._effective_exposure = self.liability_exposure * (
            1.0 - self.safety_investment_rate
        )

    # ══════════════════════════════════════════════════════════════
    #  Market Operations (ledger transfers)
    # ══════════════════════════════════════════════════════════════

    def produce(self) -> float:
        """Compute and record output for this period."""
        self.current_output = self.production_function(self.labor_count)
        return self.current_output

    def sell_output(self) -> float:
        """
        Sell produced output on the market.

        Revenue = Q * price * demand_factor.
        Demand factor is a simple scalar (1.0 = can sell all output).
        Revenue is added to the business via the ledger (from SYSTEM).

        Returns recorded revenue.
        """
        q = self.current_output
        if q <= 0:
            return 0.0

        revenue = q * self.price * self.market_demand_factor

        # Revenue flows from the market (SYSTEM entity) to the business
        # In a full simulation this would be from consumers; for now
        # we use SYSTEM as the counterparty.
        sys_id = "system"
        if not self.ledger.entity_exists(sys_id):
            self.ledger.register_entity(sys_id, EntityType.SYSTEM, initial_cash=1e12)

        self.ledger.transfer(
            from_id=sys_id,
            to_id=self.id,
            mechanism="revenue",
            amount=min(revenue, 1e9),  # sanity cap
            description=f"Product sales: {self.id} Q={q:.1f} @ ${self.price:.2f}",
        )
        self.current_revenue = min(revenue, 1e9)
        return self.current_revenue

    def pay_wages(self) -> float:
        """
        Pay wages to all workers via ledger transfers.

        Each worker receives market_wage.  This models a simplified
        labour market — in the full simulation worker IDs would be
        genuine agent references.

        Returns total wage bill.
        """
        wage_bill = self.market_wage * self.labor_count
        if wage_bill <= 0:
            return 0.0

        # Check we can afford it
        if self.cash < wage_bill:
            # Can't afford full payroll — proportional reduction
            wage_bill = max(self.cash, 0.0)

        # Pay each worker (aggregated as a single transfer to SYSTEM
        # for simplicity in this standalone agent — in full simulation
        # each worker gets individual payment)
        if wage_bill > 0:
            self.ledger.transfer(
                from_id=self.id,
                to_id="system",
                mechanism="wage",
                amount=wage_bill,
                description=f"Wages: {self.id} → workers (${wage_bill:.2f})",
            )

        self.current_wage_bill = wage_bill
        return wage_bill

    def buy_insurance(self, available_insurers: Optional[list[str]] = None) -> Optional[dict]:
        """
        Purchase liability insurance if available and affordable.

        Premium is proportional to:
            premium = base_rate * effective_exposure * revenue * loading

        The business chooses the cheapest available insurer.

        Parameters
        ----------
        available_insurers : list of str, optional
            List of insurer IDs to consider.

        Returns
        -------
        dict or None — insurance policy record.
        """
        if not available_insurers:
            # No insurers in the market — self-insure
            self.insurance_policy = None
            return None

        # Pick the cheapest insurer
        best_insurer = None
        best_premium = float('inf')

        for ins_id in available_insurers:
            premium = self._quote_premium(ins_id)
            if premium < best_premium and premium <= self.cash * 0.2:
                best_premium = premium
                best_insurer = ins_id

        if best_insurer is None:
            self.insurance_policy = None
            return None

        # Pay premium via ledger
        coverage_limit = self.current_revenue * self.DEFAULT_COVERAGE_TARGET

        self.ledger.transfer(
            from_id=self.id,
            to_id=best_insurer,
            mechanism="premium",
            amount=best_premium,
            description=f"Insurance premium: {self.id} → {best_insurer}",
        )

        self.insurance_policy = {
            "insurer_id": best_insurer,
            "premium": best_premium,
            "coverage_limit": coverage_limit,
            "effective_exposure": self._effective_exposure,
        }
        return self.insurance_policy

    def _quote_premium(self, insurer_id: str) -> float:
        """
        Quote an insurance premium from a given insurer.

        Simple formula:
            premium = base_rate * effective_exposure * coverage_target * loading
        """
        base_rate = 0.05
        loading = 1.30
        coverage_target = self.current_revenue * self.DEFAULT_COVERAGE_TARGET
        premium = base_rate * self._effective_exposure * coverage_target * loading
        return max(premium, 10.0)  # floor

    # ══════════════════════════════════════════════════════════════
    #  Accident / Liability Risk
    # ══════════════════════════════════════════════════════════════

    def handle_accident_risk(self) -> dict:
        """
        Roll the dice on accident events this period.

        With probability = effective_exposure, an accident occurs,
        causing a liability cost proportional to the business size.

        If insured, the insurance covers up to the coverage limit;
        the business pays the remainder.

        Returns a dict describing the accident outcome.
        """
        self.accidents_this_step = 0
        self.liability_costs_this_step = 0.0

        if random.random() >= self._effective_exposure:
            return {
                "accident": False,
                "liability_cost": 0.0,
                "covered_by_insurance": 0.0,
                "out_of_pocket": 0.0,
            }

        # Accident occurs
        self.accidents_this_step = 1

        # Liability cost proportional to scale
        base_liability = (
            0.10 * self.current_revenue
            + 0.02 * self.capital
        )
        liability_cost = random.uniform(base_liability * 0.5, base_liability * 1.5)

        # Apply insurance coverage
        covered = 0.0
        if self.insurance_policy is not None:
            covered = min(liability_cost, self.insurance_policy["coverage_limit"])
            # Record claim against insurer via ledger
            try:
                self.ledger.transfer(
                    from_id=self.insurance_policy["insurer_id"],
                    to_id=self.id,
                    mechanism="claim",
                    amount=covered,
                    description=f"Liability claim: {self.insurance_policy['insurer_id']} → {self.id}",
                )
            except Exception:
                covered = 0.0  # insurer couldn't pay

        out_of_pocket = liability_cost - covered

        # Pay out-of-pocket liability cost
        if out_of_pocket > 0:
            pay_amount = min(out_of_pocket, max(self.cash, 0.0))
            self.ledger.transfer(
                from_id=self.id,
                to_id="system",
                mechanism="liability",
                amount=pay_amount,
                description=f"Liability payment: {self.id} → system (${pay_amount:.2f})",
            )

        self.liability_costs_this_step = out_of_pocket

        return {
            "accident": True,
            "liability_cost": round(liability_cost, 2),
            "covered_by_insurance": round(covered, 2),
            "out_of_pocket": round(out_of_pocket, 2),
        }

    # ══════════════════════════════════════════════════════════════
    #  Investment
    # ══════════════════════════════════════════════════════════════

    def invest_in_expansion(self) -> float:
        """
        Reinvest a fraction of profit into capital stock.

        Investment = max(0, profit * reinvestment_rate).
        Capital increases by the investment amount.
        Money is recorded as spent through the ledger.

        Returns investment amount.
        """
        # Compute period profit
        self.current_profit = (
            self.current_revenue
            - self.current_wage_bill
            - (self.insurance_policy["premium"] if self.insurance_policy else 0.0)
            - self.liability_costs_this_step
        )

        investment = max(0.0, self.current_profit * self.reinvestment_rate)

        if investment > 0 and self.cash >= investment:
            self.ledger.transfer(
                from_id=self.id,
                to_id="system",
                mechanism="investment",
                amount=investment,
                description=f"Capital investment: {self.id} (${investment:.2f})",
            )
            self.capital += investment
        elif investment > 0:
            # Invest what we can
            affordable = max(self.cash, 0.0)
            if affordable > 0:
                self.ledger.transfer(
                    from_id=self.id,
                    to_id="system",
                    mechanism="investment",
                    amount=affordable,
                    description=f"Capital investment (partial): {self.id} (${affordable:.2f})",
                )
                self.capital += affordable
                investment = affordable

        self.current_investment = investment
        return investment

    # ══════════════════════════════════════════════════════════════
    #  Main Step
    # ══════════════════════════════════════════════════════════════

    def step(
        self,
        *,
        market_wage: Optional[float] = None,
        market_demand_factor: Optional[float] = None,
        available_insurers: Optional[list[str]] = None,
    ) -> dict:
        """
        Execute one simulation step.

        Decision order:
          1. Decide hiring (adjust workforce)
          2. Decide safety investment
          3. Produce output
          4. Set price
          5. Sell output
          6. Pay wages
          7. Buy insurance
          8. Handle accident risk
          9. Invest in expansion

        Parameters
        ----------
        market_wage : float, optional
            Current market wage per worker.
        market_demand_factor : float, optional
            Demand scalar (1.0 = unconstrained).
        available_insurers : list of str, optional
            Insurer IDs available for policy purchase.

        Returns
        -------
        dict — summary of this step's decisions and outcomes.
        """
        if not self.alive:
            return {"status": "dead", "agent_id": self.id}

        # Update market context
        if market_wage is not None:
            self.market_wage = market_wage
        if market_demand_factor is not None:
            self.market_demand_factor = market_demand_factor

        # Reset period accounting
        self.reset_period_accounting()

        # ── Decision sequence ────────────────────────────────────

        # 1. Hiring
        net_hires = self.decide_hiring()

        # 2. Safety investment
        self.decide_safety_investment()

        # 3. Production
        self.produce()

        # 4. Pricing
        self.decide_price()

        # 5. Sell
        self.sell_output()

        # 6. Pay wages
        self.pay_wages()

        # 7. Insurance
        policy = self.buy_insurance(available_insurers)

        # 8. Accident risk
        accident = self.handle_accident_risk()

        # 9. Investment
        self.invest_in_expansion()

        # ── Bankruptcy counter update ─────────────────────────────
        # Track consecutive steps where cash < 0 AND net worth < 0
        if self.cash < 0 and self.net_worth < 0:
            self._consecutive_negative_steps += 1
        else:
            self._consecutive_negative_steps = 0

        return {
            "agent_id": self.id,
            "step": self.ledger.step,
            "workers": self.labor_count,
            "net_hires": net_hires,
            "capital": round(self.capital, 2),
            "output": round(self.current_output, 2),
            "price": round(self.price, 2),
            "revenue": round(self.current_revenue, 2),
            "wage_bill": round(self.current_wage_bill, 2),
            "insurance_premium": round(
                policy["premium"] if policy else 0.0, 2
            ),
            "has_insurance": policy is not None,
            "accident": accident,
            "investment": round(self.current_investment, 2),
            "profit": round(self.current_profit, 2),
            "cash": round(self.cash, 2),
            "net_worth": round(self.net_worth, 2),
        }

    def reset_period_accounting(self):
        """Zero out per-period accounting fields."""
        self.current_output = 0.0
        self.current_revenue = 0.0
        self.current_wage_bill = 0.0
        self.current_profit = 0.0
        self.current_investment = 0.0
        self.accidents_this_step = 0
        self.liability_costs_this_step = 0.0

    # ══════════════════════════════════════════════════════════════
    #  Bankruptcy
    # ══════════════════════════════════════════════════════════════

    @property
    def should_bankrupt(self) -> bool:
        """Check if business meets 3-consecutive-step bankruptcy threshold.

        Returns True when cash < 0 AND net worth < 0 for 3+ consecutive
        steps and the business is still alive.
        """
        return self._consecutive_negative_steps >= 3 and self.alive

    def liquidate(self) -> dict:
        """Liquidate the business on bankruptcy.

        Steps:
          1. Sell off capital (transfer from system, reversing prior investment).
          2. Distribute remaining cash to system.
          3. Zero out capital and lay off all workers.
          4. Mark as dead.

        Returns a dict with liquidation details.
        """
        if not self.alive:
            return {"status": "already_dead", "agent_id": self.id}

        capital_value = self.capital
        workers_laid_off = self.labor_count

        # 1. Liquidate capital — convert capital stock to cash
        #    (reverse of invest_in_expansion: system pays for capital assets)
        if capital_value > 0:
            self.ledger.transfer(
                from_id="system",
                to_id=self.id,
                mechanism="bankruptcy_liquidation",
                amount=capital_value,
                description=(
                    f"Capital liquidation: {self.id} "
                    f"sells ${capital_value:.2f} in capital assets"
                ),
            )

        self.capital = 0.0

        # 2. Distribute remaining cash to system (creditors / public)
        remaining_cash = max(0.0, self.cash)
        if remaining_cash > 0:
            self.ledger.transfer(
                from_id=self.id,
                to_id="system",
                mechanism="bankruptcy_liquidation",
                amount=remaining_cash,
                description=(
                    f"Bankruptcy distribution: {self.id} "
                    f"distributes ${remaining_cash:.2f}"
                ),
            )

        # 3. Lay off all workers
        self.workers_hired.clear()

        # 4. Mark dead
        self.alive = False
        self._consecutive_negative_steps = 0

        return {
            "agent_id": self.id,
            "capital_liquidated": round(capital_value, 2),
            "workers_laid_off": workers_laid_off,
            "distributed_cash": round(remaining_cash, 2),
        }

    # ══════════════════════════════════════════════════════════════
    #  Reporting
    # ══════════════════════════════════════════════════════════════

    def get_status(self) -> dict:
        """Return a snapshot of the business's current state."""
        return {
            "id": self.id,
            "alive": self.alive,
            "cash": round(self.cash, 2),
            "capital": round(self.capital, 2),
            "workers": self.labor_count,
            "price": round(self.price, 2),
            "liability_exposure": self.liability_exposure,
            "effective_exposure": round(self._effective_exposure, 4),
            "safety_investment_rate": self.safety_investment_rate,
            "has_insurance": self.insurance_policy is not None,
            "insurance_premium": round(
                self.insurance_policy["premium"], 2
            ) if self.insurance_policy else 0.0,
            "tfp": self.tfp,
            "capital_share": self.capital_share,
            "net_worth": round(self.net_worth, 2),
        }

    def to_dict(self) -> dict:
        """Serialise for export."""
        return self.get_status()


# ══════════════════════════════════════════════════════════════════════
#  Demonstration
# ══════════════════════════════════════════════════════════════════════

def demo():
    """
    Run a comprehensive demonstration of the BusinessAgent.

    Shows:
      - Business creation and ledger registration
      - Multi-step simulation with hiring, production, pricing
      - Wage payments and revenue through the ledger
      - Insurance purchase and premium payment
      - Accident events with insurance coverage
      - Capital investment and expansion
      - Zero-sum invariant enforcement
    """
    import sys
    import os

    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _src_dir = os.path.normpath(os.path.join(_script_dir, ".."))
    if _src_dir not in sys.path:
        sys.path.insert(0, _src_dir)

    print("═" * 70)
    print("BUSINESS AGENT — DEMONSTRATION")
    print("═" * 70)

    # ── 1. Setup ─────────────────────────────────────────────────
    ledger = LedgerEngine(step_log=False)
    ledger.register_entity("system", EntityType.SYSTEM, initial_cash=1e9)

    # Create a business
    biz = BusinessAgent(
        "acme_corp",
        ledger,
        initial_cash=200_000.0,
        initial_capital=150_000.0,
        liability_exposure=0.08,
        market_wage=18.0,
        tfp=1.2,
        capital_share=0.35,
        markup=1.25,
        tick_created=0,
    )

    print(f"\n─── Business Created ───")
    status = biz.get_status()
    for k, v in status.items():
        print(f"  {k:25s} = {v}")

    # ── 2. Single Step ───────────────────────────────────────────
    print(f"\n─── Step 1: First Operations ───")
    ledger.begin_step()
    result = biz.step(market_wage=18.0, market_demand_factor=1.0)
    ledger.close_step()
    for k, v in result.items():
        if isinstance(v, dict):
            print(f"  {k:25s} = {v}")
        else:
            print(f"  {k:25s} = {v}")

    bs = ledger.get_balance("acme_corp")
    print(f"\n  Ledger cash: ${bs.cash:.2f}")
    print(f"  Workers: {biz.labor_count}")
    print(f"  Capital: ${biz.capital:.2f}")

    # ── 3. Multi-step run ────────────────────────────────────────
    print(f"\n─── Steps 2–10: Ongoing Operations ───")

    mock_insurers = ["safe_insure", "risk_accept"]
    for ins_id in mock_insurers:
        ledger.register_entity(ins_id, EntityType.INSURER, initial_cash=500_000.0)

    for step_num in range(2, 11):
        ledger.begin_step()
        result = biz.step(
            market_wage=18.0 + random.uniform(-1.0, 1.0),
            market_demand_factor=random.uniform(0.85, 1.15),
            available_insurers=mock_insurers,
        )
        metrics = ledger.close_step()

        acc_flag = "⚠️ " if result["accident"]["accident"] else "   "
        print(
            f"  Step {step_num:2d}{acc_flag}"
            f"  workers={result['workers']:2d}"
            f"  output={result['output']:>8.1f}"
            f"  price=${result['price']:<6.2f}"
            f"  rev=${result['revenue']:<8.2f}"
            f"  profit=${result['profit']:<8.2f}"
            f"  cash=${result['cash']:<8.2f}"
            f"  capital=${result['capital']:<8.2f}"
            f"  insured={result['has_insurance']}"
        )

        if result["accident"]["accident"]:
            print(
                f"         Liability: cost=${result['accident']['liability_cost']:>8.2f}"
                f"  covered=${result['accident']['covered_by_insurance']:>8.2f}"
                f"  oop=${result['accident']['out_of_pocket']:>8.2f}"
            )

    # ── 4. Growth trajectory ─────────────────────────────────────
    print(f"\n─── Growth Trajectory (Step 11–30) ───")
    for step_num in range(11, 31):
        ledger.begin_step()
        result = biz.step(
            market_wage=19.0 + math.sin(step_num * 0.3) * 1.5,
            market_demand_factor=1.0 + math.sin(step_num * 0.2) * 0.1,
            available_insurers=mock_insurers,
        )
        ledger.close_step()

        if step_num % 5 == 0 or result["accident"]["accident"]:
            acc = "⚠️ ACCIDENT" if result["accident"]["accident"] else "          "
            print(
                f"  Step {step_num:2d}  {acc}"
                f"  workers={result['workers']:3d}"
                f"  capital=${result['capital']:<9.2f}"
                f"  rev=${result['revenue']:<8.2f}"
                f"  profit=${result['profit']:<8.2f}"
                f"  cash=${result['cash']:<9.2f}"
            )

    # ── 5. Liquidation scenario ──────────────────────────────────
    print(f"\n─── Stress Test: Market Downturn ───")
    for step_num in range(31, 41):
        # Crushing demand and rising wages
        ledger.begin_step()
        result = biz.step(
            market_wage=22.0 + step_num * 0.5,    # rising wages
            market_demand_factor=max(0.1, 1.0 - (step_num - 30) * 0.08),  # falling demand
            available_insurers=mock_insurers,
        )
        metrics = ledger.close_step()

        print(
            f"  Step {step_num:2d}"
            f"  demand={biz.market_demand_factor:.2f}"
            f"  wage=${biz.market_wage:.0f}"
            f"  workers={result['workers']:2d}"
            f"  rev=${result['revenue']:<8.2f}"
            f"  profit=${result['profit']:<8.2f}"
            f"  cash=${result['cash']:<8.2f}"
            f"  capital=${result['capital']:<9.2f}"
        )

        if biz.cash < 0 and biz.alive:
            print(f"    → Insolvent! Terminating.")
            biz.alive = False
            break

    # ── 6. Ledger verification ───────────────────────────────────
    print(f"\n─── Ledger Verification ───")
    total_money = sum(bs.cash for bs in ledger.balances.values())
    print(f"  Total money in system: ${total_money:.2f}")
    print(f"  Total transfers:       {len(ledger.transfers)}")
    print(f"  Total ledger entries:  {len(ledger.entries)}")
    print(f"  Steps executed:        {ledger.step}")

    all_balanced = all(m["balanced"] for m in ledger.step_metrics)
    print(f"  All steps balanced:    {all_balanced}")
    if not all_balanced:
        for m in ledger.step_metrics:
            if not m["balanced"]:
                print(f"    Step {m['step']}: imbalance={m['imbalance']:.6f}")

    # Flow summary
    for mech in ("revenue", "wage", "premium", "claim", "liability", "investment"):
        total = ledger.get_total_flow(mech)
        if total > 0:
            print(f"  Total '{mech}' flow:    ${total:.2f}")

    # ── Final state ──────────────────────────────────────────────
    print(f"\n─── Final Business State ───")
    status = biz.get_status()
    for k, v in status.items():
        print(f"  {k:25s} = {v}")

    print(f"\n{'═' * 70}")
    print("DEMONSTRATION COMPLETE")
    print(f"{'═' * 70}")

    return biz, ledger


# ══════════════════════════════════════════════════════════════════════
#  Runner
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    demo()
