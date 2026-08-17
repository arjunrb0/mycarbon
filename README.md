# MyCarbon — Personal Carbon Footprint Calculator & Reduction Optimizer

A Streamlit web application that estimates an individual's annual CO₂
footprint from their lifestyle, then uses **combinatorial optimization** to
recommend which reduction actions to take under a fixed budget.

🌐 **Live:** https://mycarbon.streamlit.app

| Tool / Language | Purpose |
| --------------- | ------- |
| Python | Calculation logic, optimization algorithms |
| Streamlit | User interface and web deployment |
| Plotly / Matplotlib | On-screen charts and PDF figures |
| fpdf2 | Multi-page PDF report generation |
| pytest | Test suite, including a brute-force reference solver |
| GitHub | Version control |

---

## What it does

1. **Estimates** annual emissions across seven categories — transportation,
   electricity, diet, housing, waste, water and appliances — from user inputs.
2. **Compares** the result against a documented average-Indian profile.
3. **Optimises** a reduction plan: given a yearly rupee budget, it selects the
   combination of actions that cuts the most CO₂.
4. **Reports** everything as an on-screen dashboard and a downloadable
   multi-page PDF.

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
**a third of budgets tested**.

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
electricity charging it. This moved "switch to an EV" from 6th to 13th in the
optimizer's ranking, and promoted rooftop solar and carpooling — which is the
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

### Known limitations

- Diet factors are from a **UK** cohort. Indian non-vegetarian diets contain
  far less red meat (so the figure is likely too high), while Indian
  vegetarian diets are dairy-heavy (so that figure is likely too low) — the
  gap between them is probably **narrower** in India than modelled.
- Air travel and consumption of goods and services are **not modelled at all**.
  Totals should be read as a lower bound.
- Housing and water factors involve uncited assumptions, flagged `LOW`.
- The "India average" is a documented urban, grid-connected, vehicle-owning
  profile — deliberately **not** the national per-capita mean, which is much
  lower because many Indians own no vehicle.

---

## Running it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Compare the solvers from the command line:

```bash
python3 optimizer.py
```

Run the tests:

```bash
python3 -m pytest tests/ -q
```

---

## Tests

70 tests covering the optimizer and the emission factor data.

The most important is a **property test against a brute-force reference
solver**. Brute force enumerates all 2ⁿ subsets and is the definition of the
correct answer, so any disagreement means the DP is wrong. It runs over 60
randomised instances plus the real catalogue at every budget.

The factor tests are mostly **unit-range assertions** — deliberately so. The
worst bug in this project was dimensional, and no amount of algorithm testing
would have caught a per-litre value used per kilometre. An assertion that road
transport must fall between 0.02 and 0.5 kg/km would have.

One of these tests found a real gap while being written: a `LOW`-confidence
factor with no caveat documenting why.

---

## Project structure

```
app.py                       Streamlit navigation
views/advanced.py            Calculator page, charts, PDF generation
views/about_me.py            About page
optimizer.py                 Knapsack model and the four solvers
emission_factors.py          Sourced factors, shared baseline calculation
tests/                       pytest suite
```

---

## Planned

- Effort-points as an alternative to rupees, for users without a budget
- Session saving and footprint history over time
- Geo-aware tips based on state-level grid factors
- Sequential rather than independent savings (submodular optimization — a
  materially harder problem than knapsack)

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
