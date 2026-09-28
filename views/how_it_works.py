"""
How the calculator and planner work. Every worked example on this page is
computed live by the same solver code the calculator uses — nothing here is a
hand-typed illustration that could drift out of sync with the real thing.
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pandas as pd
import streamlit as st

import charts
import emission_factors as ef
import inputs as I
import optimizer as opt
import ui

ui.inject_css()

ui.hero(
    "How MyCarbon works",
    "The footprint is multiplication. The planner is a classic optimisation problem — "
    "and the most interesting bugs were in the model, not the code.",
    eyebrow="Under the hood",
)


def toy(name, cost, saving, group=None):
    action = opt.Action(name, "Example", cost, lambda b, i, s=saving: s,
                        exclusive_group=group)
    return opt.ScoredAction(action=action, saving=saving)


# ── 1. The problem ───────────────────────────────────────────────────────────
ui.section("1 · Choosing changes is a knapsack problem",
           "You can't do everything, so which subset of changes saves the most?")
st.markdown(
    "Each possible change has a **cost** and a **CO₂ saving**, and you have a **budget**. "
    "Picking the best subset is exactly the *0/1 knapsack problem* from computer "
    "science — the classic puzzle of packing the most valuable items into a bag "
    "that can only carry so much weight."
)
l, r = st.columns([3, 2], gap="large")
with l:
    st.latex(r"\text{maximise}\ \sum_i s_i x_i \quad \text{subject to}\ "
             r"\sum_i c_i x_i \le B,\quad x_i \in \{0, 1\}")
    st.markdown(
        "- **0/1**, because you can't install 40% of a solar panel and get 40% of the "
        "benefit — each change is all-or-nothing.\n"
        "- Not *unbounded*, because you can't switch to an electric scooter twice.\n"
        "- With *n* possible changes there are 2ⁿ combinations. At 20 changes that's "
        "over a million, and the problem is NP-hard in general."
    )
with r:
    st.dataframe(
        pd.DataFrame({"Knapsack": ["Item", "Weight", "Value", "Bag capacity"],
                      "MyCarbon": ["A change you could make", "Its yearly cost (₹)",
                                   "CO₂ it saves (kg/yr)", "Your yearly budget"]}),
        hide_index=True, width="stretch",
    )

# ── 2. Why the obvious shortcut fails ────────────────────────────────────────
ui.section("2 · Why “best value first” isn't good enough",
           "The shortcut: keep taking whichever change saves the most CO₂ per rupee.")
items = [toy("A · LED lighting", 20, 30), toy("B · Solar panel", 90, 110),
         toy("C · Better appliances", 80, 70)]
BUDGET = 100
greedy = opt.solve_greedy(items, BUDGET)
best = opt.solve_dp(items, BUDGET, granularity=1)
st.dataframe(
    pd.DataFrame([{"Change": s.name, "Cost (₹)": int(s.cost), "Saves (kg)": int(s.saving),
                   "kg per ₹": round(s.density, 2),
                   "Shortcut picks": "✅" if s in greedy.chosen else "",
                   "Best plan picks": "✅" if s in best.chosen else ""}
                  for s in items]),
    hide_index=True, width="stretch",
)
st.markdown(
    f"With a **₹{BUDGET}** budget the shortcut grabs A first — it has the best ratio — "
    f"and that leaves only ₹{BUDGET - 20}, too little for B. It saves "
    f"**{greedy.total_saving:.0f} kg**. The best plan skips the 'best value' item "
    f"entirely and saves **{best.total_saving:.0f} kg**. Choices are linked through the "
    f"shared budget, so no rule that scores changes one at a time can see this."
)
st.info(
    "The shortcut can be *arbitrarily* bad: with one change worth 2 kg for ₹1 and another "
    "worth B kg for ₹B, it takes the first and gets 2 kg out of a possible B. Taking the "
    "better of {the shortcut, the single best change} fixes this and is guaranteed to be "
    "at least half as good as the best plan.", icon="💡")

# ── 3. Dynamic programming ───────────────────────────────────────────────────
ui.section("3 · Solving it exactly with dynamic programming")
st.markdown(
    "Rather than trying all 2ⁿ combinations, fill in a table. Each cell answers one "
    "small question: *using only the first i changes and budget c, what's the most I can "
    "save?* Each answer reuses ones already worked out:"
)
st.latex(r"\text{best}[i][c] = \max\big(\underbrace{\text{best}[i-1][c]}_{\text{skip change } i},"
         r"\ \underbrace{\text{best}[i-1][c - \text{cost}_i] + \text{saving}_i}"
         r"_{\text{make change } i}\big)")
weights, cap = opt._discretise(items, BUDGET, 10)
dp, _ = opt._grouped_table(items, weights, cap, use_groups=False)
table = pd.DataFrame(
    [[round(v) for v in row] for row in dp],
    index=["(no changes)"] + [f"+ {s.name}" for s in items],
    columns=[f"₹{c * 10}" for c in range(cap + 1)],
)
st.dataframe(table, width="stretch")
st.caption(
    "The table for the example above, in ₹10 steps. The bottom-right cell is the answer. "
    "Any two combinations that reach the same row and budget are interchangeable from "
    "then on, which is why a table of n × B cells replaces 2ⁿ combinations. "
    "(It's 'pseudo-polynomial': the work grows with the size of the budget number, "
    "which is why MyCarbon counts money in ₹100 steps.)"
)

# ── 4. Diminishing returns ───────────────────────────────────────────────────
ui.section("4 · One table answers every budget at once",
           "The bottom row of the table is the best saving at every budget — plotted "
           "below for the calculator's example household.")
ex = {**I.DEFAULTS, **I.EXAMPLE_PROFILE}
ex_actions = opt.build_actions(ef.compute_baseline_kg(ex), ex)
st.plotly_chart(
    charts.frontier_chart(opt.optimal_frontier(ex_actions, 120_000),
                          opt.greedy_frontier(ex_actions, 120_000)),
    width="stretch", config={"displayModeBar": False},
)
st.markdown(
    "This is also how the **Reach a target** mode works without a new algorithm. "
    "Flipping the question to *what's the cheapest way to save X kg?* just means finding "
    "the first budget where this curve crosses X — the curve can only go up, because a "
    "bigger budget never forces a worse plan."
)

# ── 5. The bugs ──────────────────────────────────────────────────────────────
ui.section("5 · Two bugs that taught me the most",
           "Neither caused an error message. Both produced confident, plausible numbers.")
b1, b2 = st.columns(2, gap="medium")
with b1:
    with st.container(border=True, height="stretch"):
        st.markdown("#### The commute counted four times")
        st.markdown(
            "The first working planner recommended carpooling, the metro, cycling **and** "
            "an electric car — for the same commute — and added all four savings. It "
            "claimed to remove **117%** of the user's driving emissions.\n\n"
            "Knapsack assumes savings simply add up. These don't: they're alternatives. "
            "The fix is a *multiple-choice knapsack*, where changes to the same thing form "
            "a group and at most one per group can be chosen. The headline number halved "
            "— and became possible."
        )
with b2:
    with st.container(border=True, height="stretch"):
        st.markdown("#### Litres mistaken for kilometres")
        st.markdown(
            "Petrol releases **2.31 kg of CO₂ per litre**. The original code multiplied "
            "that by kilometres driven, so a 40 km commute came out at **34 tonnes** a "
            "year — more than the average American emits in total.\n\n"
            "Dividing by fuel economy (~15 km/l) gives 0.154 kg per km. The test suite "
            "now checks that every transport factor is in a physically sensible range, "
            "which would have caught this immediately."
        )

# ── 6. Trust ─────────────────────────────────────────────────────────────────
ui.section("6 · Why you can trust the numbers (and where you shouldn't)")
st.markdown(
    f"- **Checked against brute force.** Tests compare the planner with a program that "
    f"tries every combination, on dozens of random problems. Any disagreement would mean "
    f"the planner is wrong.\n"
    f"- **Every factor is sourced**, including India's own grid factor of "
    f"{ef.ELECTRICITY.value} kg CO₂ per kWh from the Central Electricity Authority.\n"
    f"- **Results are ranges.** Each factor is rated High, Medium or Low confidence, and "
    f"the likely range widens for the weaker ones.\n"
    f"- **Known gaps:** the diet data comes from a UK study, flights and shopping aren't "
    f"counted, and change costs are rough estimates. Read the total as a lower bound."
)
st.page_link("views/calculator.py", label="Try the calculator",
             icon=":material/calculate:")

ui.footer()
