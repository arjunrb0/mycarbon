"""
The downloadable PDF report.

Kept separate from the page so it can be tested without a browser, and so the
page script stays about layout. Charts are drawn with matplotlib in the same
palette as the on-screen Plotly charts, and embedded straight from memory — no
temporary files to leak or clean up.
"""

import io
from datetime import datetime

import matplotlib
matplotlib.use("Agg")            # headless: no display on a server
import matplotlib.pyplot as plt
from fpdf import FPDF
from fpdf.enums import XPos, YPos

import emission_factors as ef
import insights
import optimizer

BLUE, GREY, INK, INK_2, GRID = "#2a78d6", "#898781", "#16201a", "#52514e", "#e1e0d9"
GREEN_RGB = (31, 122, 77)
NEXT = dict(new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def clean(text: str) -> str:
    """The PDF's built-in Helvetica only covers Latin-1, so map everything else."""
    text = str(text)
    for a, b in {"—": "-", "–": "-", "’": "'", "‘": "'", "“": '"', "”": '"',
                 "₹": "Rs ", "₂": "2", "…": "...", "•": "-", "≈": "~", "°": " deg"}.items():
        text = text.replace(a, b)
    return text.encode("latin-1", "ignore").decode("latin-1")


# ── Charts ───────────────────────────────────────────────────────────────────
def _style(ax):
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7")
    ax.tick_params(colors=INK_2, labelsize=9, length=0)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _png(fig) -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def breakdown_png(baseline_kg: dict, ranges_kg: dict) -> io.BytesIO:
    cats = [c for c in baseline_kg
            if baseline_kg[c] > 0 or ef.INDIA_AVERAGES.get(c, 0) > 0]
    cats.sort(key=lambda c: baseline_kg[c])
    y = range(len(cats))
    fig, ax = plt.subplots(figsize=(8, 0.5 + 0.48 * len(cats)))
    h = 0.36
    ax.barh([i - h / 2 for i in y], [ef.INDIA_AVERAGES.get(c, 0) for c in cats],
            height=h, color=GREY, label="Typical urban Indian")
    you = [baseline_kg[c] / 1000 for c in cats]
    err = [[(baseline_kg[c] - ranges_kg[c][0]) / 1000 for c in cats],
           [(ranges_kg[c][2] - baseline_kg[c]) / 1000 for c in cats]]
    ax.barh([i + h / 2 for i in y], you, height=h, color=BLUE, label="You",
            xerr=err, error_kw=dict(ecolor=INK_2, elinewidth=1, capsize=2))
    ax.set_yticks(list(y), cats)
    ax.set_xlabel("tonnes CO2e per year", color=INK_2, fontsize=9)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], labels[::-1], frameon=False, fontsize=9, loc="lower right")
    _style(ax)
    return _png(fig)


def before_after_png(before_kg: dict, after_kg: dict) -> io.BytesIO:
    cats = [c for c in before_kg if after_kg.get(c, 0) < before_kg[c] - 1e-9]
    cats.sort(key=lambda c: before_kg[c])
    y = range(len(cats))
    fig, ax = plt.subplots(figsize=(8, 0.6 + 0.5 * max(1, len(cats))))
    h = 0.36
    ax.barh([i - h / 2 for i in y], [before_kg[c] / 1000 for c in cats],
            height=h, color=GREY, label="Now")
    ax.barh([i + h / 2 for i in y], [after_kg[c] / 1000 for c in cats],
            height=h, color=BLUE, label="With this plan")
    ax.set_yticks(list(y), cats)
    ax.set_xlabel("tonnes CO2e per year", color=INK_2, fontsize=9)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], labels[::-1], frameon=False, fontsize=9, loc="lower right")
    _style(ax)
    return _png(fig)


# ── Document ─────────────────────────────────────────────────────────────────
class _PDF(FPDF):
    def __init__(self, title):
        super().__init__()
        self.doc_title = title
        self.set_auto_page_break(auto=True, margin=16)

    def header(self):
        self.set_fill_color(*GREEN_RGB)
        self.rect(0, 0, 210, 24, "F")
        self.set_xy(10, 7)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(255, 255, 255)
        self.cell(130, 8, clean(self.doc_title))
        self.set_font("Helvetica", "", 9)
        self.cell(0, 8, datetime.now().strftime("%d %B %Y"), align="R")
        self.set_text_color(*_hex(INK))
        self.set_y(32)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(137, 135, 129)
        self.cell(0, 6, f"MyCarbon  |  mycarbon.streamlit.app  |  Page {self.page_no()}",
                  align="C")

    def h2(self, text):
        self.ln(2)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*GREEN_RGB)
        self.cell(0, 8, clean(text), **NEXT)
        self.set_draw_color(225, 224, 217)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)
        self.set_text_color(*_hex(INK))

    def para(self, text, size=10, color=INK):
        self.set_font("Helvetica", "", size)
        self.set_text_color(*_hex(color))
        self.multi_cell(0, 5.2, clean(text), **NEXT)
        self.set_text_color(*_hex(INK))

    def table(self, header, rows, widths, align=None):
        align = align or ["L"] + ["C"] * (len(header) - 1)
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(*GREEN_RGB)
        self.set_text_color(255, 255, 255)
        for h, w, a in zip(header, widths, align):
            self.cell(w, 7, clean(h), fill=True, align=a)
        self.ln(7)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*_hex(INK))
        for i, row in enumerate(rows):
            self.set_fill_color(*((246, 248, 245) if i % 2 == 0 else (255, 255, 255)))
            for cell, w, a in zip(row, widths, align):
                self.cell(w, 6.2, clean(cell), fill=True, align=a)
            self.ln(6.2)


def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def build_pdf(name: str, inputs: dict, plan=None, plan_label: str = "") -> bytes:
    baseline = ef.compute_baseline_kg(inputs)
    ranges = ef.baseline_range_kg(inputs)
    total = sum(baseline.values())
    lo, _, hi = ranges["Total"]
    who = name.strip()
    pdf = _PDF(f"{who}'s Carbon Footprint Report" if who else "Your Carbon Footprint Report")

    # ── Page 1: summary ───────────────────────────────────────────────────
    pdf.add_page()
    head, story = insights.verdict(total)
    pdf.set_font("Helvetica", "B", 30)
    pdf.set_text_color(*GREEN_RGB)
    pdf.cell(0, 13, f"{total / 1000:.2f} t CO2e / year", **NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*_hex(INK_2))
    pdf.cell(0, 6, clean(f"Likely range {lo / 1000:.1f}-{hi / 1000:.1f} t, per person. {head}."),
             **NEXT)
    pdf.ln(2)
    pdf.para(story)
    pdf.ln(1)
    pdf.table(
        ["Reference point", "Tonnes CO2e per person per year"],
        [["You", f"{total / 1000:.2f}"],
         ["Typical urban Indian (same method)", f"{ef.INDIA_AVERAGES['Total']:.2f}"],
         ["1.5 deg C lifestyle level for 2030", f"{ef.LIFESTYLE_TARGET_2030.value:.2f}"],
         ["India national per-capita CO2 (energy & industry)",
          f"{ef.INDIA_NATIONAL_PER_CAPITA.value:.2f}"],
         ["World average", f"{ef.WORLD_AVERAGE_PER_CAPITA:.2f}"]],
        [130, 60],
    )
    pdf.h2("Where your emissions come from")
    pdf.image(breakdown_png(baseline, ranges), x=12, w=180)

    # ── Page 2: the plan ──────────────────────────────────────────────────
    if plan is not None and plan.chosen:
        after = optimizer.projected_baseline(baseline, plan)
        cut = total - sum(after.values())
        pdf.add_page()
        pdf.h2("Your reduction plan")
        pdf.para(
            f"{plan_label} Chosen by dynamic programming, which compares combinations "
            f"of actions rather than ranking them one at a time, and treats actions "
            f"that cut the same emissions (such as different ways of changing one "
            f"commute) as alternatives so no saving is counted twice."
        )
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, clean(
            f"Saves {cut / 1000:.2f} t a year ({cut / total:.0%}) for about "
            f"Rs {plan.total_cost:,.0f} a year."), **NEXT)
        pdf.ln(1)
        rows = [[s.name, s.category, f"{s.cost:,.0f}", f"{s.saving:,.0f}"]
                for s in sorted(plan.chosen, key=lambda a: -a.saving)]
        rows.append(["Total", "", f"{plan.total_cost:,.0f}", f"{plan.total_saving:,.0f}"])
        pdf.table(["Action", "Category", "Your cost (Rs/yr)", "Saves (kg/yr)"],
                  rows, [82, 36, 36, 36])
        pdf.ln(4)
        pdf.image(before_after_png(baseline, after), x=12, w=180)
        pdf.ln(2)
        pdf.para(
            "Costs are indicative annual estimates: one-off purchases are spread over "
            "their useful life, and household items such as solar panels are split "
            "between the people who share the home.", size=8, color=INK_2)

    # ── Page 3: detail and next steps ─────────────────────────────────────
    pdf.add_page()
    pdf.h2("Category detail")
    factors = ef.category_factors(inputs)
    rows = []
    for cat in sorted(baseline, key=lambda c: -baseline[c]):
        clo, _, chi = ranges[cat]
        f = factors.get(cat)
        rows.append([cat, f"{baseline[cat] / 1000:.2f}",
                     f"{clo / 1000:.2f}-{chi / 1000:.2f}",
                     f"{ef.INDIA_AVERAGES.get(cat, 0):.2f}",
                     f.confidence.title() if f and baseline[cat] > 0 else "-"])
    pdf.table(["Category", "You (t)", "Likely range", "Typical (t)", "Data quality"],
              rows, [52, 30, 40, 32, 36])
    tip_list = insights.tips(baseline)
    pdf.h2("Where to focus")
    if tip_list:
        for cat, tip in tip_list:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, clean(cat), **NEXT)
            pdf.para(tip)
            pdf.ln(1)
    else:
        pdf.para("Every category is at or below the typical urban Indian profile. "
                 "The planner can still show the cheapest next steps.")

    pdf.h2("How this was calculated")
    pdf.para(
        "Each input is multiplied by a published emission factor: the Central "
        "Electricity Authority's grid factor for electricity, DEFRA/IPCC fuel factors "
        "for transport, Scarborough et al. (2014) for diet, and DEFRA for landfill waste. "
        "Household electricity, appliances and floor area are divided by the number of "
        "people in the home. The likely range reflects how reliable each factor is; it "
        "does not include uncertainty in the numbers you entered. Air travel and the "
        "goods and services you buy are not included, so read the total as a lower bound.",
        size=9, color=INK_2)
    return bytes(pdf.output())
