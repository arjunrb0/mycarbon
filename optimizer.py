"""
Carbon reduction optimizer.

Given a user's baseline emissions and a budget in rupees, choose the set of
reduction actions that maximises CO2 saved without exceeding the budget.

This is the 0/1 knapsack problem:
    items    -> reduction actions
    weight   -> annualised cost in rupees
    value    -> kg CO2 saved per year
    capacity -> the user's annual budget

Stage 2 implements the greedy (value-density) heuristic only.
Stage 3 adds the exact dynamic-programming solution for comparison.
"""

import math
from dataclasses import dataclass, field
from typing import Callable, Optional

import emission_factors as ef


# ── Cost basis ───────────────────────────────────────────────────────────────
# Both sides of the ratio must be per-year or the comparison is meaningless:
# you cannot divide a one-time purchase price by an annual CO2 saving and get
# anything interpretable. So capital purchases are ANNUALISED — spread over an
# assumed useful lifetime — while recurring costs are used as-is.
#
#     annualised cost = upfront price / lifetime_years  +  running cost/year
#
# Every rupee figure below is a placeholder to be replaced with a sourced
# value in stage 4. They are order-of-magnitude plausible for India in 2026,
# but they are not yet cited and should not be presented as fact.


@dataclass(frozen=True)
class Action:
    """One candidate reduction action."""

    name: str
    category: str
    cost: float                       # annualised rupees per year
    saving_fn: Callable[[dict, dict], float]   # (baseline_kg, inputs) -> kg CO2/yr
    detail: str = ""
    exclusive_group: Optional[str] = None
    """Actions sharing a group are alternatives — at most one may be chosen.

    Set this only where two actions genuinely attack the SAME flow of
    emissions. Actions in the same category are not automatically exclusive:
    composting (wet waste) and recycling (dry waste) touch different streams
    and really do add up. Over-grouping loses real, achievable savings.
    """

    def saving(self, baseline: dict, inputs: dict) -> float:
        return max(0.0, float(self.saving_fn(baseline, inputs)))


@dataclass(frozen=True)
class ScoredAction:
    """An Action with its saving resolved against a specific user's profile."""

    action: Action
    saving: float                     # kg CO2/yr
    cost_share: Optional[float] = None
    """This user's share of the cost, when it differs from the catalogue price.

    Household-level actions (solar, LEDs, appliances) are bought once and
    shared by everyone in the home, so each person's share is the price
    divided by household size — matching how their per-person emissions are
    computed. Leaving the full price on a per-person saving would make every
    household action look several times worse value than it is.
    """

    @property
    def name(self) -> str:
        return self.action.name

    @property
    def category(self) -> str:
        return self.action.category

    @property
    def cost(self) -> float:
        return self.action.cost if self.cost_share is None else self.cost_share

    @property
    def detail(self) -> str:
        return self.action.detail

    @property
    def exclusive_group(self) -> Optional[str]:
        return self.action.exclusive_group

    @property
    def density(self) -> float:
        """kg CO2 saved per rupee spent — the greedy ranking key."""
        return self.saving / self.cost if self.cost > 0 else float("inf")


@dataclass
class Solution:
    """The result of running an optimizer."""

    method: str
    chosen: list = field(default_factory=list)   # list[ScoredAction]
    total_saving: float = 0.0                    # kg CO2/yr
    total_cost: float = 0.0                      # rupees/yr
    budget: float = 0.0

    @property
    def leftover(self) -> float:
        return self.budget - self.total_cost


# ── The action catalogue ─────────────────────────────────────────────────────
# Savings are expressed as a fraction of the relevant baseline category, so a
# heavy commuter gets a bigger estimated saving from the same action than a
# light one. This is what makes the recommendations personalised rather than a
# static lookup table.
#
# NOTE (deliberate, stage 2): several of these actions overlap. "Carpool",
# "Public transport" and "Switch to an EV" all attack the same petrol
# emissions, and "Go vegetarian" / "Go vegan" are alternatives, not a bundle.
# Plain 0/1 knapsack treats every item as independent and additive, so it will
# happily recommend all of them and sum their savings. That double-counting is
# left in on purpose — see the exclusivity discussion in stage 3.


def _frac(category: str, fraction: float):
    """Saving function: a flat fraction of one baseline category."""
    return lambda baseline, inputs: baseline.get(category, 0.0) * fraction


def _transport_switch(target_fuel: str):
    """Saving from swapping the current fuel for a cleaner one."""

    factors = {k: f.value for k, f in ef.TRANSPORT_PER_KM.items()}
    target_factor = factors[target_fuel]

    def fn(baseline, inputs):
        current = inputs.get("fuel_type")
        if current not in factors:
            return 0.0
        current_factor = factors[current]
        if target_factor >= current_factor:
            return 0.0          # not an improvement for this user
        reduction = (current_factor - target_factor) / current_factor
        return baseline.get("Transportation", 0.0) * reduction

    return fn


def _diet_switch(target_diet: str):
    """Saving from moving to a lower-carbon diet."""

    factors = {k: f.value for k, f in ef.DIET_PER_DAY.items()}

    def fn(baseline, inputs):
        current = inputs.get("diet")
        if current not in factors or target_diet not in factors:
            return 0.0
        current_factor = factors[current]
        target = factors[target_diet]
        if target >= current_factor:
            return 0.0
        reduction = (current_factor - target) / current_factor
        return baseline.get("Diet", 0.0) * reduction

    return fn


def _meatfree_days(days_per_week: int):
    """Partial diet shift: swap N days a week to vegetarian."""

    def fn(baseline, inputs):
        if inputs.get("diet") != "Non-Vegetarian":
            return 0.0
        nonveg = ef.DIET_PER_DAY["Non-Vegetarian"].value
        veg = ef.DIET_PER_DAY["Vegetarian"].value
        reduction = (nonveg - veg) / nonveg * (days_per_week / 7)
        return baseline.get("Diet", 0.0) * reduction

    return fn


ACTION_CATALOGUE = [
    # ── Transportation ───────────────────────────────────────────────────
    Action(
        "Carpool with one other person",
        "Transportation",
        cost=2_000,
        saving_fn=_frac("Transportation", 0.50),
        detail="Halves per-person commute emissions. Cost is a share of fuel and coordination overhead.",
        exclusive_group="commute",
    ),
    Action(
        "Public transport for half the commute",
        "Transportation",
        cost=12_000,
        saving_fn=_frac("Transportation", 0.45),
        detail="Metro or bus pass. Assumes half the commute shifts off private vehicle.",
        exclusive_group="commute",
    ),
    Action(
        "Cycle or walk trips under 5 km",
        "Transportation",
        cost=8_000,
        saving_fn=_frac("Transportation", 0.22),
        detail="Bicycle amortised over five years. Short trips are the least efficient per km.",
        exclusive_group="commute",
    ),
    Action(
        "Switch to an electric car",
        "Transportation",
        cost=85_000,
        saving_fn=_transport_switch("Electric"),
        detail="Price premium over petrol, annualised over ten years. On India's coal-heavy "
               "grid this saves far less than intuition suggests — see emission_factors.py.",
        exclusive_group="commute",
    ),
    Action(
        "Switch to an electric two-wheeler",
        "Transportation",
        cost=4_000,
        saving_fn=_transport_switch("Two-wheeler (electric)"),
        detail="Electric scooter price premium over a petrol one, annualised over eight "
               "years. For a car driver this assumes the commute works on two wheels.",
        exclusive_group="commute",
    ),
    # ── Electricity ──────────────────────────────────────────────────────
    Action(
        "Replace all bulbs with LEDs",
        "Electricity",
        cost=3_000,
        saving_fn=_frac("Electricity", 0.12),
        detail="Lighting is roughly 15% of a typical Indian household load; LEDs cut it by ~75%.",
    ),
    Action(
        "Smart power strips for standby loads",
        "Electricity",
        cost=2_500,
        saving_fn=_frac("Electricity", 0.05),
        detail="Eliminates phantom draw from idle electronics.",
    ),
    Action(
        "Install 1 kW rooftop solar",
        "Electricity",
        cost=18_000,
        saving_fn=_frac("Electricity", 0.55),
        detail="Post-subsidy install cost annualised over fifteen years.",
    ),
    Action(
        "Cool-roof paint and window shading",
        "Electricity",
        cost=15_000,
        saving_fn=_frac("Electricity", 0.10),
        detail="Reduces cooling load. Booked against electricity, not housing — see modelling notes.",
    ),
    # ── Appliances ───────────────────────────────────────────────────────
    Action(
        "Upgrade to 5-star BEE-rated appliances",
        "Appliances",
        cost=20_000,
        saving_fn=_frac("Appliances", 0.35),
        detail="Replacement premium annualised over ten years.",
    ),
    # ── Diet ─────────────────────────────────────────────────────────────
    Action(
        "Two meat-free days per week",
        "Diet",
        cost=1_000,
        saving_fn=_meatfree_days(2),
        detail="A partial shift, easiest to sustain. Cost covers substitute proteins.",
        exclusive_group="diet",
    ),
    Action(
        "Switch to a vegetarian diet",
        "Diet",
        cost=2_000,
        saving_fn=_diet_switch("Vegetarian"),
        detail="Full shift away from meat.",
        exclusive_group="diet",
    ),
    Action(
        "Switch to a vegan diet",
        "Diet",
        cost=6_000,
        saving_fn=_diet_switch("Vegan"),
        detail="Full shift away from all animal products.",
        exclusive_group="diet",
    ),
    # ── Waste ────────────────────────────────────────────────────────────
    Action(
        "Home composting for organic waste",
        "Waste",
        cost=3_500,
        saving_fn=_frac("Waste", 0.40),
        detail="Diverts the wet fraction from landfill, avoiding methane.",
    ),
    Action(
        "Segregate and recycle dry waste",
        "Waste",
        cost=1_000,
        saving_fn=_frac("Waste", 0.25),
        detail="Bins and collection. Mostly an effort cost.",
    ),
    # ── Water ────────────────────────────────────────────────────────────
    Action(
        "Fix leaking taps and fittings",
        "Water",
        cost=1_500,
        saving_fn=_frac("Water", 0.10),
        detail="A dripping tap wastes roughly 15 litres a day.",
    ),
    Action(
        "Low-flow showerheads and aerators",
        "Water",
        cost=4_000,
        saving_fn=_frac("Water", 0.30),
        detail="Cuts flow rate without a noticeable change in use.",
    ),
    Action(
        "Rainwater harvesting system",
        "Water",
        cost=20_000,
        saving_fn=_frac("Water", 0.40),
        detail="Install cost annualised over fifteen years.",
    ),
]


# Categories whose actions are bought once for the whole home. Transport and
# diet are personal choices, so their cost stays with the individual.
HOUSEHOLD_CATEGORIES = {"Electricity", "Appliances", "Water", "Waste", "Housing"}


def build_actions(baseline: dict, inputs: dict, catalogue=None) -> list:
    """Resolve the catalogue against one user's profile.

    Actions that would save nothing for this user — an EV recommendation for
    someone who already drives electric, a vegetarian recommendation for
    someone already vegetarian — are dropped rather than offered at zero value.
    """
    catalogue = ACTION_CATALOGUE if catalogue is None else catalogue
    people = max(1.0, float(inputs.get("household_size", 1) or 1))
    scored = []
    for action in catalogue:
        saving = action.saving(baseline, inputs)
        if saving > 0 and action.cost > 0:
            share = (action.cost / people
                     if action.category in HOUSEHOLD_CATEGORIES else None)
            scored.append(ScoredAction(action=action, saving=saving, cost_share=share))
    return scored


# ── Greedy solver ────────────────────────────────────────────────────────────
def solve_greedy(scored_actions: list, budget: float,
                 respect_groups: bool = False) -> Solution:
    """Rank by CO2 saved per rupee, then take everything that still fits.

    O(n log n), dominated by the sort.

    Note the 'still fits' rather than 'stop at the first that does not fit'.
    Skipping an unaffordable item and carrying on is never worse and is often
    better — it lets cheap high-density items backfill the leftover budget.

    respect_groups=True also skips any action whose exclusive group is already
    taken. That puts greedy on the same, corrected objective as
    solve_dp_grouped, so comparing the two isolates the ALGORITHM's loss
    rather than mixing it up with the double-counting bug.
    """
    ranked = sorted(
        scored_actions,
        key=lambda s: (-s.density, -s.saving, s.name),   # deterministic ties
    )

    chosen, spent, saved, taken = [], 0.0, 0.0, set()
    for item in ranked:
        group = item.exclusive_group if respect_groups else None
        if group is not None and group in taken:
            continue
        if spent + item.cost <= budget:
            chosen.append(item)
            spent += item.cost
            saved += item.saving
            if group is not None:
                taken.add(group)

    return Solution(
        method="Greedy (CO₂ per rupee)",
        chosen=chosen,
        total_saving=saved,
        total_cost=spent,
        budget=budget,
    )


def greedy_ranking(scored_actions: list) -> list:
    """The full density-ordered list, for showing the user the reasoning."""
    return sorted(
        scored_actions,
        key=lambda s: (-s.density, -s.saving, s.name),
    )


def solve_greedy_half_approx(scored_actions: list, budget: float) -> Solution:
    """Greedy, plus the single best affordable action, whichever is better.

    Plain greedy has NO constant-factor guarantee: with items (value 2, cost 1)
    and (value B, cost B) under budget B, greedy takes the first and returns 2
    against an optimum of B, so its ratio tends to zero as B grows.

    Taking the better of {greedy, best single item} fixes that and yields a
    1/2-approximation — the result is provably within a factor of two of
    optimal. Kept separate from solve_greedy so the DP comparison below comes
    out clean.
    """
    best = solve_greedy(scored_actions, budget)

    affordable = [s for s in scored_actions if s.cost <= budget]
    if affordable:
        top = max(affordable, key=lambda s: (s.saving, -s.cost, s.name))
        if top.saving > best.total_saving:
            best = Solution(
                method="Greedy (½-approx fallback: single best action)",
                chosen=[top],
                total_saving=top.saving,
                total_cost=top.cost,
                budget=budget,
            )
    return best


# ── Exact solver: dynamic programming ────────────────────────────────────────
# The DP needs INTEGER weights, and runs in O(n * B) where B is the budget in
# whatever unit we discretise to. That is *pseudo-polynomial*: linear in the
# numeric value of B, but exponential in the number of bits used to write B
# down. Doubling the budget doubles the work; adding one digit multiplies it
# by ten. This is why 0/1 knapsack stays NP-hard despite having a "fast" DP.
#
# Rupee budgets are large (₹150,000), so we discretise to units of GRANULARITY
# rupees. At ₹100 that turns a 150,000-column table into a 1,500-column one — a
# 100x saving. Catalogue prices are multiples of ₹500, so the answer is exact
# for a one-person household; household shares (price / household size) are
# not round numbers, and rounding them up to the next ₹100 can very
# occasionally miss a plan that would just have fit.
#
# Rounding direction matters: costs round UP and the budget rounds DOWN, so a
# plan the DP calls affordable is always genuinely affordable. Erring the other
# way could return a plan the user cannot pay for.

GRANULARITY = 100


def _discretise(scored_actions: list, budget: float, granularity: int):
    weights = [max(1, math.ceil(s.cost / granularity)) for s in scored_actions]
    capacity = int(budget // granularity)
    return weights, capacity


def solve_dp(scored_actions: list, budget: float, granularity: int = GRANULARITY) -> Solution:
    """Exact 0/1 knapsack by dynamic programming.

    dp[i][c] = the most CO2 saveable using only the first i actions within
    budget c. Each cell asks one question: is it better to skip action i, or
    to take it and spend the rest of the budget optimally on the actions
    before it?

        dp[i][c] = max( dp[i-1][c],                    # skip
                        dp[i-1][c - w_i] + v_i )       # take

    The reason this beats brute force: there are 2^n subsets but only
    n * B distinct (i, c) states, and every subset reaching the same state is
    interchangeable from there on. The table collapses the exponential search
    into a polynomial number of decisions.

    Runs in O(n * B) time and space. The table is kept (rather than the
    usual 1-D rolling array) so the chosen set can be recovered by
    backtracking.
    """
    n = len(scored_actions)
    weights, capacity = _discretise(scored_actions, budget, granularity)
    values = [s.saving for s in scored_actions]

    if n == 0 or capacity <= 0:
        return Solution(method="Dynamic programming (exact)", budget=budget)

    dp = [[0.0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        w_i, v_i = weights[i - 1], values[i - 1]
        prev, row = dp[i - 1], dp[i]
        for c in range(capacity + 1):
            best = prev[c]
            if w_i <= c:
                take = prev[c - w_i] + v_i
                if take > best:
                    best = take
            row[c] = best

    # Backtrack: action i was taken iff including it changed the answer.
    chosen, c = [], capacity
    for i in range(n, 0, -1):
        if dp[i][c] != dp[i - 1][c]:
            chosen.append(scored_actions[i - 1])
            c -= weights[i - 1]
    chosen.reverse()

    return Solution(
        method="Dynamic programming (exact)",
        chosen=chosen,
        total_saving=sum(s.saving for s in chosen),
        total_cost=sum(s.cost for s in chosen),
        budget=budget,
    )


def solve_dp_grouped(scored_actions: list, budget: float,
                     granularity: int = GRANULARITY) -> Solution:
    """Multiple-choice knapsack: at most one action per exclusive group.

    This is the fix for the double-counting seen in stage 2. Actions that
    attack the same flow of emissions share an exclusive_group, and the DP is
    restructured to iterate over GROUPS rather than individual actions. At
    each group it picks the best of: take nothing from this group, or take
    exactly one of its members.

        dp[g][c] = max( dp[g-1][c],
                        max over items j in group g of
                            dp[g-1][c - w_j] + v_j )

    Ungrouped actions become singleton groups, which reduces exactly to the
    plain 0/1 case — so this generalises solve_dp rather than replacing it.
    Complexity is unchanged at O(n * B): the inner loop still touches each
    action once per budget column.
    """
    n = len(scored_actions)
    weights, capacity = _discretise(scored_actions, budget, granularity)

    if n == 0 or capacity <= 0:
        return Solution(method="DP + exclusivity groups (exact)", budget=budget)

    table = _grouped_table(scored_actions, weights, capacity)
    chosen = _backtrack(scored_actions, weights, table, capacity)
    return Solution(
        method="DP + exclusivity groups (exact)",
        chosen=chosen,
        total_saving=sum(s.saving for s in chosen),
        total_cost=sum(s.cost for s in chosen),
        budget=budget,
    )


def _grouped_table(scored_actions: list, weights: list, capacity: int,
                   use_groups: bool = True):
    """Build the multiple-choice knapsack table once, for every budget up to
    `capacity`. Returns (dp, pick).

    The bottom row, dp[-1][c], is the best saving achievable within budget c
    for EVERY c at once. That is what makes the frontier and target mode
    cheap: one table answers every budget question, rather than re-solving
    the problem from scratch for each one.

    With use_groups=False every action becomes its own group, which is
    exactly plain 0/1 knapsack — used to draw the naive curve for comparison.
    """
    values = [s.saving for s in scored_actions]

    groups, order = {}, []
    for idx, s in enumerate(scored_actions):
        key = (s.exclusive_group if use_groups else None) or f"__solo_{idx}"
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(idx)

    g_count = len(order)
    dp = [[0.0] * (capacity + 1) for _ in range(g_count + 1)]
    # pick[g][c] = index of the action chosen from group g, or None.
    pick = [[None] * (capacity + 1) for _ in range(g_count + 1)]

    for g in range(1, g_count + 1):
        members = groups[order[g - 1]]
        prev, row, prow = dp[g - 1], dp[g], pick[g]
        for c in range(capacity + 1):
            best, best_idx = prev[c], None          # take nothing from group
            for j in members:
                if weights[j] <= c:
                    take = prev[c - weights[j]] + values[j]
                    if take > best:
                        best, best_idx = take, j
            row[c] = best
            prow[c] = best_idx
    return dp, pick


def _backtrack(scored_actions, weights, table, c):
    """Recover the chosen actions for budget column c."""
    _, pick = table
    chosen = []
    for g in range(len(pick) - 1, 0, -1):
        j = pick[g][c]
        if j is not None:
            chosen.append(scored_actions[j])
            c -= weights[j]
    chosen.reverse()
    return chosen


def optimal_frontier(scored_actions: list, max_budget: float, step: float = 1_000,
                     granularity: int = GRANULARITY, use_groups: bool = True) -> list:
    """The best achievable saving at every budget from 0 to max_budget.

    Returns [(budget, kg_saved), ...]. Plotted, this is the curve of
    diminishing returns: the first few thousand rupees buy the cheap,
    high-impact actions, and each extra rupee after that buys less.
    """
    weights, capacity = _discretise(scored_actions, max_budget, granularity)
    if not scored_actions or capacity <= 0:
        return [(0.0, 0.0)]
    dp, _ = _grouped_table(scored_actions, weights, capacity, use_groups)
    last = dp[-1]
    points, b = [], 0.0
    while b <= max_budget + 1e-9:
        points.append((b, last[int(b // granularity)]))
        b += step
    return points


def greedy_frontier(scored_actions: list, max_budget: float, step: float = 1_000,
                    respect_groups: bool = True) -> list:
    """Greedy's saving at every budget, for plotting against the optimum."""
    points, b = [], 0.0
    while b <= max_budget + 1e-9:
        points.append((b, solve_greedy(scored_actions, b, respect_groups).total_saving))
        b += step
    return points


def solve_min_cost_for_target(scored_actions: list, target_kg: float,
                              granularity: int = GRANULARITY):
    """The cheapest plan that saves at least target_kg per year.

    This is the problem turned inside out. Instead of "most CO2 for my
    budget" it asks "least money for my goal":

        minimise  sum(c_i x_i)   subject to   sum(s_i x_i) >= target

    It needs no new algorithm. dp[-1][c] is the best saving within budget c,
    and it can only rise as c rises (a bigger budget never forces a worse
    plan). So the cheapest budget that reaches the target is simply the
    FIRST column where the bottom row crosses it — found by scanning the same
    table the budget mode builds.

    Returns (solution, max_achievable_kg). solution is None when even taking
    every useful action cannot reach the target.
    """
    total_cost = sum(s.cost for s in scored_actions)
    weights, capacity = _discretise(scored_actions, total_cost + granularity, granularity)
    if not scored_actions or capacity <= 0:
        return None, 0.0
    table = _grouped_table(scored_actions, weights, capacity)
    last = table[0][-1]
    max_kg = last[capacity]
    if target_kg <= 0:
        return Solution(method="Cheapest plan for target", budget=0.0), max_kg

    for c in range(capacity + 1):
        if last[c] >= target_kg - 1e-9:
            chosen = _backtrack(scored_actions, weights, table, c)
            return Solution(
                method="Cheapest plan for target",
                chosen=chosen,
                total_saving=sum(s.saving for s in chosen),
                total_cost=sum(s.cost for s in chosen),
                budget=c * granularity,
            ), max_kg
    return None, max_kg


# ── Reporting helpers ────────────────────────────────────────────────────────
def category_savings(solution: Solution) -> dict:
    """Total kg CO2/yr saved per category by a plan."""
    out = {}
    for s in solution.chosen:
        out[s.category] = out.get(s.category, 0.0) + s.saving
    return out


def projected_baseline(baseline: dict, solution: Solution) -> dict:
    """The user's emissions after the plan is carried out.

    Clamped at zero: a category cannot emit a negative amount. If the clamp
    ever actually bites, the model is over-claiming somewhere — the grouped
    solver exists to stop that happening, but the floor stays as a guard.
    """
    saved = category_savings(solution)
    return {
        cat: max(0.0, value - saved.get(cat, 0.0))
        for cat, value in baseline.items()
    }


# ── Verification helper ──────────────────────────────────────────────────────
def solve_brute_force(scored_actions: list, budget: float) -> Solution:
    """Try all 2^n subsets. Only for testing the DP on small inputs.

    This is the definition of the right answer. If the DP disagrees with it,
    the DP is wrong.
    """
    n = len(scored_actions)
    if n > 22:
        raise ValueError(f"{n} actions is {2**n:,} subsets — too many.")

    best_val, best_set = 0.0, ()
    for mask in range(1 << n):
        cost = saving = 0.0
        for i in range(n):
            if mask & (1 << i):
                cost += scored_actions[i].cost
                saving += scored_actions[i].saving
        if cost <= budget and saving > best_val:
            best_val, best_set = saving, tuple(
                scored_actions[i] for i in range(n) if mask & (1 << i)
            )

    return Solution(
        method="Brute force (reference)",
        chosen=list(best_set),
        total_saving=best_val,
        total_cost=sum(s.cost for s in best_set),
        budget=budget,
    )


# ── Manual check ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # A heavy-footprint profile: long petrol commute, high electricity use,
    # non-vegetarian diet.
    demo_inputs = {
        "distance": 40, "fuel_type": "Petrol",
        "electricity": 400, "appliances": 12,
        "diet": "Non-Vegetarian", "meals": 3,
        "house_material": "Brick", "house_size": 1200,
        "water": 200, "waste": 8,
    }
    demo_baseline = {
        "Transportation": ef.TRANSPORT_PER_KM["Petrol"].value * 40 * 365,
        "Electricity": ef.ELECTRICITY.value * 400 * 12,
        "Diet": ef.DIET_PER_DAY["Non-Vegetarian"].value * (3 / ef.DIET_REFERENCE_MEALS) * 365,
        "Waste": ef.WASTE.value * 8 * 52,
        "Water": ef.WATER.value * 200 * 365,
        "Appliances": ef.APPLIANCE_EMBODIED.value * 12,
        "Housing": ef.HOUSING_PER_SQFT_YEAR["Brick"].value * 1200,
    }
    print("Baseline (corrected factors):")
    for k, v in sorted(demo_baseline.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<16} {v:>9,.0f} kg CO₂/yr")
    print(f"  {'TOTAL':<16} {sum(demo_baseline.values()):>9,.0f} kg CO₂/yr "
          f"= {sum(demo_baseline.values())/1000:.2f} t\n")

    actions = build_actions(demo_baseline, demo_inputs)
    print(f"{len(actions)} applicable actions\n")

    print("Density ranking (kg CO₂ saved per ₹):")
    for s in greedy_ranking(actions):
        print(f"  {s.density:8.4f}  {s.saving:9.1f} kg  ₹{s.cost:>7,.0f}  {s.name}")

    def show(result):
        print(f"\n{result.method} — ₹{result.budget:,.0f} budget")
        for s in result.chosen:
            print(f"  ₹{s.cost:>7,.0f}  {s.saving:9.1f} kg  {s.name}")
        print(f"  TOTAL {result.total_saving:>10,.0f} kg CO₂/yr "
              f"for ₹{result.total_cost:,.0f} (₹{result.leftover:,.0f} unspent)")

    # ── 1. Is the DP actually correct? ───────────────────────────────────
    print("\n" + "=" * 72)
    print("DP vs brute force (is the DP right?)")
    print("=" * 72)
    mismatches = 0
    for b in range(2_000, 120_001, 2_000):
        dp_r = solve_dp(actions, b)
        bf_r = solve_brute_force(actions, b)
        if abs(dp_r.total_saving - bf_r.total_saving) > 1e-6:
            mismatches += 1
            print(f"  MISMATCH at ₹{b:,}: dp={dp_r.total_saving:.1f} "
                  f"brute={bf_r.total_saving:.1f}")
    print(f"  {mismatches} mismatches across 60 budgets "
          f"({'DP verified exact' if mismatches == 0 else 'DP IS WRONG'})")

    # ── 2. Where does greedy fall short of the exact answer? ─────────────
    print("\n" + "=" * 72)
    print("Greedy vs DP — budgets where they disagree")
    print("=" * 72)
    gaps = []
    for b in range(2_000, 120_001, 1_000):
        g = solve_greedy(actions, b)
        d = solve_dp(actions, b)
        if d.total_saving - g.total_saving > 1e-6:
            gaps.append((b, g.total_saving, d.total_saving))
    if gaps:
        worst = max(gaps, key=lambda t: (t[2] - t[1]) / t[2])
        print(f"  greedy is suboptimal at {len(gaps)} of 119 budgets tested")
        print(f"  worst case: ₹{worst[0]:,} — greedy {worst[1]:,.0f} kg "
              f"vs optimal {worst[2]:,.0f} kg "
              f"({(1 - worst[1]/worst[2])*100:.1f}% short)")
        b = worst[0]
        show(solve_greedy(actions, b))
        show(solve_dp(actions, b))
    else:
        print("  greedy matched the optimum at every budget tested")

    # ── 3. What the exclusivity fix changes ──────────────────────────────
    print("\n" + "=" * 72)
    print("Ignoring overlap vs respecting it")
    print("=" * 72)
    b = 30_000
    naive = solve_dp(actions, b)
    fixed = solve_dp_grouped(actions, b)
    show(naive)
    show(fixed)

    transport_baseline = demo_baseline["Transportation"]
    naive_transport = sum(s.saving for s in naive.chosen
                          if s.category == "Transportation")
    fixed_transport = sum(s.saving for s in fixed.chosen
                          if s.category == "Transportation")
    print(f"\n  Transportation baseline:     {transport_baseline:>10,.0f} kg/yr")
    print(f"  claimed saved, no grouping:  {naive_transport:>10,.0f} kg/yr"
          f"  {'← IMPOSSIBLE' if naive_transport > transport_baseline else ''}")
    print(f"  claimed saved, with grouping:{fixed_transport:>10,.0f} kg/yr"
          f"  {'← IMPOSSIBLE' if fixed_transport > transport_baseline else ''}")
