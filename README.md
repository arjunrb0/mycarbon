# MyCarbon — Carbon Footprint Calculator & Reduction Planner

[![tests](https://github.com/arjunrb0/mycarbon/actions/workflows/tests.yml/badge.svg)](https://github.com/arjunrb0/mycarbon/actions/workflows/tests.yml)

A web app that estimates a person's yearly carbon footprint from how they live,
using Indian data wherever it exists, and then uses **combinatorial
optimization** to find the combination of changes that saves the most CO₂ for
the money they're willing to spend.

🌐 **Live:** https://mycarbon.streamlit.app

| Tool | Purpose |
| --- | --- |
| Python | Calculation logic and optimization algorithms |
| Streamlit | Interface and deployment |
| Plotly / Matplotlib | On-screen charts and PDF figures |
| fpdf2 | PDF report |
| pytest + GitHub Actions | 120 tests on every push, including a brute-force reference solver and end-to-end tests of the app |

---

## What it does

- **Live footprint** across seven categories that updates as you type. There's no
  Calculate button, so nothing disappears when you touch another control.
- **Honest numbers.** Every emission factor is traced to a source and rated for
  reliability, and the result is shown as a likely range, not a falsely precise
  single number.
- **Fair comparisons.** You're compared with a typical urban Indian computed by
  the same code, and with the 2.5 t per-person level for the 1.5°C goal by 2030.
- **A reduction planner** with two modes: *spend a set budget* (most CO₂ for
  your money) or *reach a target* (cheapest way to cut X%).
- **Algorithm comparison** that plots the exact solver against the greedy
  shortcut for your own details.
- **PDF report and share links.** Links reopen the calculator with your details
  filled in, and never include your name.
- **"Try an example"** fills in a realistic household, so a first visitor sees
  every feature at once.
- A **How it works** page that walks through the algorithm with examples
  computed live by the same code.
- Works on phones.

---

## The optimizer

This is the core of the project. The problem is:

> Given a set of possible reduction actions, each with a CO₂ saving and a
> cost, and a limited budget — which subset should you do?

### Modelling it as 0/1 knapsack

With *n* actions, where $s_i$ is the CO₂ saved, $c_i$ the annualised cost, and
$x_i \in \{0,1\}$ whether the action is taken:

$$\text{maximize} \ \sum_{i} s_i x_i \quad \text{subject to} \ \sum_{i} c_i x_i \le B$$

This is exactly the **0/1 knapsack problem** with the nouns renamed:

| Knapsack | MyCarbon |
| --- | --- |
| Item | Reduction action |
| Weight | Annualised cost (₹) |
| Value | kg CO₂ saved per year |
| Capacity | User's annual budget |

**Why 0/1 and not fractional?** You cannot install 40% of a rooftop solar
system and get 40% of the savings — installation has a threshold, and value
isn't linear in the fraction. **Why not unbounded?** You can't switch to an EV
three times.

**Why it's hard:** choices are coupled through the shared budget. No
single-item ranking can see that two mediocre actions may jointly beat one
excellent action, because taking one changes what's affordable afterwards.
With *n* actions there are 2ⁿ subsets, and the problem is NP-hard.

Savings are computed from the **user's own inputs**, not hardcoded — switching
to public transport saves a 40 km/day commuter far more than a 4 km/day one.

### Three solvers, for comparison

| Solver | Complexity | Guarantee |
| --- | --- | --- |
| `solve_greedy` | O(n log n) | None — can be arbitrarily far from optimal |
| `solve_greedy_half_approx` | O(n log n) | Within a factor of 2 of optimal |
| `solve_dp` | O(n·B) | Exact |
| `solve_dp_grouped` | O(n·B) | Exact, and respects mutual exclusivity |
| `optimal_frontier` | O(n·B), once | The best saving at **every** budget from one table |
| `solve_min_cost_for_target` | O(n·B), once | Cheapest plan reaching a CO₂ goal |

**Greedy** ranks by CO₂-saved-per-rupee and takes whatever fits. It is provably
optimal for the *fractional* problem (by an exchange argument), when all costs
are equal, and whenever it happens to exhaust the budget exactly — that last
case is checkable at runtime. Otherwise it can fail badly: with items
(value 2, cost 1) and (value B, cost B) under budget B, greedy returns 2
against an optimum of B, so its ratio tends to **zero**. Taking the better of
{greedy, best single item} fixes this and gives a ½-approximation.

**Dynamic programming** solves it exactly:

$$\text{dp}[i][c] = \max\big(\text{dp}[i-1][c],\ \text{dp}[i-1][c - w_i] + v_i\big)$$

There are 2ⁿ subsets but only *n × B* states, and every subset reaching the
same state is interchangeable from there on — that's the collapse from
exponential to polynomial. Note it's **pseudo-polynomial**: linear in the
*value* of B, exponential in its number of digits, which is why the problem
stays NP-hard. Rupee budgets are discretised into ₹500 units to keep the table
small, with costs rounded **up** and the budget **down** so any plan reported
as affordable genuinely is.

On the real action catalogue, greedy falls short of the optimum at roughly
**a third of budgets tested**. When greedy is also made to respect the
exclusivity groups described below, it gets worse, not better: it locks in
the first commute change it meets (carpooling, the best value per rupee) and
can then never take the electric two-wheeler, which saves far more. The
calculator plots both curves for the user's own details.

### One table answers every budget — and the reverse question

The bottom row of the DP table is the best saving at *every* budget up to the
maximum, so one table draws the whole diminishing-returns curve.

The same row answers the inverse problem for free. "What's the cheapest way to
save X kg?" is

$$\text{minimize} \ \sum_i c_i x_i \quad \text{subject to} \ \sum_i s_i x_i \ge X$$

and because the best saving can only rise as the budget rises, the answer is
simply the first column where the bottom row reaches X. The calculator's
**Reach a target** mode uses exactly this, and the tests check it against
brute force.

### The interesting bug: optimising the wrong thing

Plain knapsack assumes values are **additive and independent**. Real reduction
actions aren't. The first working version recommended *carpooling, taking the
metro, cycling, and buying an EV* — all for the same commute — and summed the
savings, claiming to eliminate **117% of the user's driving emissions**.

The algorithm was correct. The **objective function** was wrong.

The fix is a **multiple-choice knapsack**: actions that attack the same flow of
emissions share an `exclusive_group`, and the DP iterates over groups, taking
at most one member from each. Grouping is applied only where overlap is
physical — commute modes are alternatives, but composting (wet waste) and
recycling (dry waste) genuinely add up, so they stay independent.

Correcting this made the headline number **50% smaller**. That's the
improvement: the first plan was impossible, the second is achievable.

---

---

## Emission factors

Every factor in [`emission_factors.py`](emission_factors.py) carries its value,
unit, source, URL, and a confidence level — `HIGH` (primary source), `MEDIUM`
(reputable but transferred from another country), `LOW` (derived with stated
assumptions). The app renders this table with limitations at the bottom of the
calculator page.

### Three dimensional errors found and fixed

1. **Transport was wrong by ~15×.** `2.31` and `2.68` are kg CO₂ **per litre**
   of petrol and diesel, but were being multiplied by **kilometres**. A
   40 km/day commute was computing as 33.7 tonnes CO₂/yr — more than the
   average American emits in total. Corrected by dividing by real-world fuel
   economy: 2.31 ÷ 15 km/l = **0.154 kg/km**.
2. **Housing charged a one-time emission annually.** Bricks are fired once, at
   construction. Now amortised over a 50-year building life.
3. **Appliances double-counted electricity** already captured by the metered
   kWh input. The category now covers manufacturing carbon only.

Fixing these took the demo profile from 40.9 t to **8.42 t CO₂/yr**.

### A finding worth highlighting

**On India's coal-heavy grid, an EV is only ~31% cleaner than petrol per km —
not the ~95% the original factors implied.** An EV is only as clean as the
electricity charging it. This moved "switch to an electric car" from 6th to near the
bottom of the optimizer's ranking (14th of 18 today), and promoted rooftop solar and carpooling — which is the
correct answer for India. The old data was actively hiding it.

### Key sources

- **Electricity:** Central Electricity Authority, *CO₂ Baseline Database for
  the Indian Power Sector* — weighted average 0.710 kg CO₂/kWh, FY 2024-25.
  (CEA publishes three different factors; the weighted average is the correct
  one for consumption accounting, as opposed to the operating margin used for
  offset baselines.)
- **Diet:** Scarborough et al. (2014), *Climatic Change* 125:179–192.
- **Fuel and waste:** UK DEFRA GHG conversion factors.
- **CO₂ per capita:** Our World in Data — India, 2.19 t (2024).
- **Two-wheelers:** ICCT two-wheeler fuel-consumption report; LBNL (2013) for
  electric scooter consumption.
- **Household size:** National Family Health Survey (NFHS-5, 2019-21).
- **2030 target:** Hot or Cool Institute, *1.5-Degree Lifestyles* (2021) —
  2.5 t CO₂e per person.

### Two-wheelers and households

- **Two-wheelers** are the most common private vehicle in India and emit about
  a third as much per km as a petrol car: 2.31 kg/l ÷ ~45 km/l = **0.051 kg/km**
  for petrol, and 33 Wh/km × the grid factor = **0.023 kg/km** for electric
  (LBNL study of Indian EVs). The original calculator had no way to enter one.
- **Household size** — electricity, appliances and floor area are shared, so
  they're divided by the number of people at home (India averages 4.4, per
  NFHS-5). Household-level changes such as rooftop solar have their cost split
  the same way, so the plan compares a per-person saving with a per-person cost.

### Results as ranges

Each factor is rated High, Medium or Low confidence, mapped to ±10%, ±25% and
±50%. The total combines those by root-sum-of-squares, which assumes errors in
different categories are independent. These bands are a stated judgement, not a
statistical confidence interval, and they cover the factors only — not errors
in what the user types.

### Known limitations

- Diet factors are from a **UK** cohort. Indian non-vegetarian diets contain
  far less red meat (so the figure is likely too high), while Indian
  vegetarian diets are dairy-heavy (so that figure is likely too low) — the
  gap between them is probably **narrower** in India than modelled.
- Air travel and consumption of goods and services are **not modelled at all**.
  Totals should be read as a lower bound.
- Housing and water factors involve uncited assumptions, flagged `LOW`.
- The "India average" is a documented urban, grid-connected, two-wheeler-commuting
  profile — deliberately **not** the national per-capita mean, which is much
  lower because many Indians own no vehicle.

---

---

## Running it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Run the tests:

```bash
pip install -r requirements-dev.txt
python -m pytest tests -q
```

---

## Tests

120 tests, run by GitHub Actions on every push.

- **Brute-force checks.** A reference solver tries all 2ⁿ combinations and is by
  definition correct. The DP, the frontier, and target mode are all compared
  against it on randomised problems. Any disagreement means the fast version is
  wrong.
- **Unit-range checks** on every emission factor. The worst bug in this project
  was a per-litre value used per kilometre, and no algorithm test could catch
  that. An assertion that road transport must fall in a sensible range per km
  would have.
- **End-to-end tests** drive the real app through Streamlit's test harness:
  results surviving further interaction (the bug that motivated the redesign),
  inputs surviving a page change, share links round-tripping, hostile links
  being clamped rather than crashing, and the PDF being generated.

Writing these found real problems twice: a Low-confidence factor with no
caveat, and a crash when a shared link produced inputs that emit nothing.

---

## Project structure

```
app.py                  Navigation and page setup
views/home.py           Landing page
views/calculator.py     Calculator, planner, report and sharing
views/how_it_works.py   The algorithm explained, with live examples
emission_factors.py     Sourced factors, the shared calculation, uncertainty ranges
optimizer.py            Knapsack model and solvers
inputs.py               Every input defined once; share-link parsing
insights.py             Plain-language verdicts and tips
charts.py               Plotly charts (colour-blind-checked palette)
report.py               PDF report
ui.py                   Shared visual components
tests/                  pytest suite
```

---

## Planned

- **State-level grid factors.** India's regional grids were unified into one
  national grid in 2013, and the Central Electricity Authority now publishes a
  single all-India factor, so there's no official state-level figure to use.
  Deriving one from each state's generation mix is possible, but that would be a
  methodology of my own rather than a sourced number.
- Public transport as a primary commute mode, which needs a sourced per-passenger-km
  factor for Indian buses and metros.
- Effort as an alternative to rupees, for people without a budget.
- Sequential rather than independent savings (submodular optimization — a
  materially harder problem than knapsack).

---

## Reflection

This project connected my interests in environmental science, mathematics and
programming. The most valuable lesson wasn't the dynamic programming — it was
discovering, twice, that **working code can be confidently wrong**. The
double-counted commute and the per-litre/per-kilometre error both ran without
raising a single exception and produced plausible-looking output. Both were
caught by asking whether the *numbers* made physical sense, not whether the
code executed.

In both cases, fixing the bug made the headline result look worse. That turns
out to be what progress looks like.

Built by Arjun Reddy.
