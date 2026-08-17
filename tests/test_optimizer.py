"""Tests for the reduction-plan optimizer.

The most important test here is `test_dp_matches_brute_force_on_random_instances`:
brute force IS the definition of the correct answer, so if the DP ever
disagrees with it, the DP is wrong. Everything else checks contracts that are
easy to break by accident — budget limits, exclusivity, non-negative results.
"""

import os
import random
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import emission_factors as ef
import optimizer as opt


# ── Fixtures ─────────────────────────────────────────────────────────────────
HEAVY_PROFILE = {
    "distance": 40, "fuel_type": "Petrol",
    "electricity": 400, "appliances": 12,
    "diet": "Non-Vegetarian", "meals": 3,
    "house_material": "Brick", "house_size": 1200,
    "water": 200, "waste": 8,
}


@pytest.fixture
def baseline():
    return ef.compute_baseline_kg(HEAVY_PROFILE)


@pytest.fixture
def actions(baseline):
    return opt.build_actions(baseline, HEAVY_PROFILE)


def make_action(name, cost, saving, group=None, category="Test"):
    """A ScoredAction with a fixed saving, for hand-built instances."""
    a = opt.Action(name, category, cost, lambda b, i, s=saving: s,
                   exclusive_group=group)
    return opt.ScoredAction(action=a, saving=saving)


# ── build_actions ────────────────────────────────────────────────────────────
def test_build_actions_produces_applicable_actions(actions):
    assert len(actions) > 5
    assert all(s.saving > 0 for s in actions)
    assert all(s.cost > 0 for s in actions)


def test_ev_dropped_for_someone_already_driving_electric():
    profile = dict(HEAVY_PROFILE, fuel_type="Electric")
    scored = opt.build_actions(ef.compute_baseline_kg(profile), profile)
    assert not any("electric vehicle" in s.name.lower() for s in scored)


def test_diet_actions_dropped_for_existing_vegan():
    profile = dict(HEAVY_PROFILE, diet="Vegan")
    scored = opt.build_actions(ef.compute_baseline_kg(profile), profile)
    assert not any(s.category == "Diet" for s in scored)


def test_vegan_offered_but_vegetarian_not_for_a_vegetarian():
    profile = dict(HEAVY_PROFILE, diet="Vegetarian")
    scored = opt.build_actions(ef.compute_baseline_kg(profile), profile)
    names = {s.name.lower() for s in scored}
    assert any("vegan" in n for n in names)
    assert not any("vegetarian diet" in n for n in names)


def test_savings_scale_with_the_users_own_inputs():
    """A heavier commuter must be offered a bigger saving for the same action."""
    light = dict(HEAVY_PROFILE, distance=5)
    heavy = dict(HEAVY_PROFILE, distance=50)

    def carpool_saving(profile):
        scored = opt.build_actions(ef.compute_baseline_kg(profile), profile)
        return next(s.saving for s in scored if "Carpool" in s.name)

    assert carpool_saving(heavy) > carpool_saving(light) * 5


# ── Greedy ───────────────────────────────────────────────────────────────────
def test_greedy_respects_the_budget(actions):
    for budget in (1_000, 5_000, 30_000, 150_000):
        assert opt.solve_greedy(actions, budget).total_cost <= budget


def test_greedy_takes_items_in_density_order():
    items = [
        make_action("cheap-efficient", 100, 500),   # 5.0 per rupee
        make_action("pricey-weak", 1000, 100),      # 0.1 per rupee
    ]
    chosen = opt.solve_greedy(items, 100).chosen
    assert [s.name for s in chosen] == ["cheap-efficient"]


def test_greedy_skips_unaffordable_and_keeps_going():
    """Stopping at the first miss would lose the third item."""
    items = [
        make_action("a", 10, 100),     # 10.0/rupee
        make_action("big", 500, 400),  # 0.8/rupee, does not fit
        make_action("c", 20, 10),      # 0.5/rupee, fits in the remainder
    ]
    names = {s.name for s in opt.solve_greedy(items, 40).chosen}
    assert names == {"a", "c"}


def test_greedy_can_be_arbitrarily_bad():
    """The classic counterexample: greedy's ratio tends to zero."""
    budget = 10_000
    items = [
        make_action("tiny-dense", 1, 2),
        make_action("huge-total", budget, budget),
    ]
    greedy = opt.solve_greedy(items, budget)
    exact = opt.solve_dp(items, budget, granularity=1)
    assert greedy.total_saving == 2
    assert exact.total_saving == budget
    assert greedy.total_saving / exact.total_saving < 0.01


def test_half_approximation_fixes_the_pathological_case():
    budget = 10_000
    items = [
        make_action("tiny-dense", 1, 2),
        make_action("huge-total", budget, budget),
    ]
    patched = opt.solve_greedy_half_approx(items, budget)
    exact = opt.solve_dp(items, budget, granularity=1)
    assert patched.total_saving >= 0.5 * exact.total_saving


def test_half_approximation_never_worse_than_plain_greedy(actions):
    for budget in range(2_000, 120_001, 6_000):
        plain = opt.solve_greedy(actions, budget).total_saving
        patched = opt.solve_greedy_half_approx(actions, budget).total_saving
        assert patched >= plain - 1e-9


# ── Dynamic programming ──────────────────────────────────────────────────────
def test_dp_matches_brute_force_on_the_real_catalogue(actions):
    for budget in range(2_000, 120_001, 4_000):
        dp = opt.solve_dp(actions, budget)
        bf = opt.solve_brute_force(actions, budget)
        assert dp.total_saving == pytest.approx(bf.total_saving), f"at ₹{budget}"


def test_dp_matches_brute_force_on_random_instances():
    """Property test. Brute force defines the right answer."""
    rng = random.Random(20260817)
    for trial in range(60):
        n = rng.randint(1, 12)
        items = [
            make_action(f"i{j}", cost=rng.randrange(1, 40),
                        saving=rng.uniform(0.5, 100))
            for j in range(n)
        ]
        budget = rng.randrange(1, 120)
        dp = opt.solve_dp(items, budget, granularity=1)
        bf = opt.solve_brute_force(items, budget)
        assert dp.total_saving == pytest.approx(bf.total_saving), (
            f"trial {trial}: n={n} budget={budget}"
        )


def test_dp_is_never_worse_than_greedy(actions):
    """Both optimise the same objective, so exact must dominate the heuristic."""
    for budget in range(2_000, 120_001, 3_000):
        greedy = opt.solve_greedy(actions, budget).total_saving
        exact = opt.solve_dp(actions, budget).total_saving
        assert exact >= greedy - 1e-9, f"at ₹{budget}"


def test_dp_beats_greedy_somewhere_on_the_real_catalogue(actions):
    """If this ever stops being true the comparison in the UI is pointless."""
    gaps = [
        b for b in range(2_000, 120_001, 1_000)
        if opt.solve_dp(actions, b).total_saving
        > opt.solve_greedy(actions, b).total_saving + 1e-9
    ]
    assert gaps, "greedy matched the optimum everywhere — expected a gap"


def test_dp_respects_the_budget(actions):
    for budget in (1_000, 7_500, 30_000, 150_000):
        assert opt.solve_dp(actions, budget).total_cost <= budget


def test_reported_totals_match_the_chosen_actions(actions):
    """Guards against backtracking returning a set inconsistent with its value."""
    for solver in (opt.solve_greedy, opt.solve_dp, opt.solve_dp_grouped):
        sol = solver(actions, 40_000)
        assert sol.total_saving == pytest.approx(sum(s.saving for s in sol.chosen))
        assert sol.total_cost == pytest.approx(sum(s.cost for s in sol.chosen))


def test_cost_discretisation_rounds_up_so_plans_stay_affordable():
    """Rounding costs down would return plans the user cannot actually pay for."""
    items = [make_action("odd", cost=1_400, saving=100)]
    sol = opt.solve_dp(items, budget=1_000, granularity=500)
    assert sol.total_cost <= 1_000
    assert sol.chosen == []


# ── Exclusivity groups ───────────────────────────────────────────────────────
def test_grouped_dp_picks_at_most_one_per_group(actions):
    for budget in range(2_000, 120_001, 2_000):
        chosen = opt.solve_dp_grouped(actions, budget).chosen
        groups = [s.exclusive_group for s in chosen if s.exclusive_group]
        assert len(groups) == len(set(groups)), f"duplicate group at ₹{budget}"


def test_grouped_dp_never_over_claims_a_category(baseline, actions):
    """The bug this solver exists to fix: claiming to save more than is emitted."""
    for budget in range(2_000, 120_001, 2_000):
        plan = opt.solve_dp_grouped(actions, budget)
        for cat, saved in opt.category_savings(plan).items():
            assert saved <= baseline[cat] + 1e-6, f"{cat} over-claimed at ₹{budget}"


def test_ungrouped_dp_does_over_claim(baseline, actions):
    """Documents the flaw, so a regression here is visible rather than silent."""
    offenders = []
    for budget in range(2_000, 120_001, 2_000):
        plan = opt.solve_dp(actions, budget)
        for cat, saved in opt.category_savings(plan).items():
            if saved > baseline[cat] + 1e-6:
                offenders.append((budget, cat))
    assert offenders, "expected the naive solver to over-claim somewhere"


def test_grouped_reduces_to_plain_dp_when_nothing_is_grouped():
    items = [make_action(f"i{j}", cost=(j + 1) * 3, saving=(j + 1) * 7)
             for j in range(8)]
    for budget in (5, 12, 30, 60):
        assert (opt.solve_dp_grouped(items, budget, granularity=1).total_saving
                == pytest.approx(opt.solve_dp(items, budget, granularity=1).total_saving))


def test_grouped_dp_prefers_the_best_member_of_a_group():
    items = [
        make_action("weak", 100, 10, group="g"),
        make_action("strong", 100, 90, group="g"),
    ]
    chosen = opt.solve_dp_grouped(items, 1_000, granularity=1).chosen
    assert [s.name for s in chosen] == ["strong"]


# ── Reporting helpers ────────────────────────────────────────────────────────
def test_projected_baseline_subtracts_savings(baseline, actions):
    plan = opt.solve_dp_grouped(actions, 30_000)
    after = opt.projected_baseline(baseline, plan)
    saved = opt.category_savings(plan)
    for cat in baseline:
        assert after[cat] == pytest.approx(max(0.0, baseline[cat] - saved.get(cat, 0)))


def test_projected_baseline_is_never_negative(baseline, actions):
    plan = opt.solve_dp(actions, 150_000)          # the over-claiming solver
    assert all(v >= 0 for v in opt.projected_baseline(baseline, plan).values())


# ── Edge cases ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize("solver", [opt.solve_greedy, opt.solve_dp, opt.solve_dp_grouped])
def test_empty_action_list(solver):
    sol = solver([], 50_000)
    assert sol.chosen == [] and sol.total_saving == 0 and sol.total_cost == 0


@pytest.mark.parametrize("solver", [opt.solve_greedy, opt.solve_dp, opt.solve_dp_grouped])
def test_zero_budget(solver, actions):
    sol = solver(actions, 0)
    assert sol.chosen == [] and sol.total_saving == 0


@pytest.mark.parametrize("solver", [opt.solve_greedy, opt.solve_dp, opt.solve_dp_grouped])
def test_budget_below_the_cheapest_action(solver, actions):
    cheapest = min(s.cost for s in actions)
    assert solver(actions, cheapest - 1).chosen == []


def test_empty_profile_yields_no_actions():
    empty = {"distance": 0, "fuel_type": "N/A", "electricity": 0, "appliances": 0,
             "diet": "N/A", "meals": 0, "house_material": "N/A", "house_size": 0,
             "water": 0, "waste": 0}
    assert opt.build_actions(ef.compute_baseline_kg(empty), empty) == []


def test_leftover_is_budget_minus_spend(actions):
    sol = opt.solve_dp(actions, 33_000)
    assert sol.leftover == pytest.approx(33_000 - sol.total_cost)
