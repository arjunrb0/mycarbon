"""
On-screen charts, built with Plotly.

Design rules followed throughout (see the palette notes below):
- "You" is always slot-1 blue; reference series (India average, "now") are a
  neutral grey, so the eye goes to the thing being discussed. Reductions are
  never shown in red/green — those are status colours, and colour alone must
  never carry meaning.
- One axis per chart, hairline gridlines, thin bars with rounded ends, a legend
  whenever there are two or more series, and a hover tooltip on every mark.
- Every chart has a table twin on the page, so no value is reachable only by
  hovering.
"""

import plotly.graph_objects as go

# Validated with the dataviz palette checker (light mode, surface #fcfcfb):
# blue/orange pass colour-blind separation (ΔE 24.7) and 3:1 contrast.
BLUE = "#2a78d6"        # categorical slot 1 — "you", the optimal plan
ORANGE = "#eb6834"      # categorical slot 2 — the comparison algorithm
GREY = "#898781"        # neutral reference series
INK = "#16201a"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'


def _layout(fig, height, x_title=None, y_title=None, legend=True):
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=16, t=36 if legend else 12, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=13, color=INK_2),
        hoverlabel=dict(bgcolor="white", bordercolor=GRID,
                        font=dict(family=FONT, color=INK, size=13)),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(color=INK_2), title=None),
        barcornerradius=4,
        bargap=0.35,
        bargroupgap=0.08,
    )
    fig.update_xaxes(title=x_title, gridcolor=GRID, linecolor=AXIS, zeroline=False,
                     tickfont=dict(color=MUTED), title_font=dict(color=INK_2))
    fig.update_yaxes(title=y_title, gridcolor=GRID, linecolor=AXIS, zeroline=False,
                     tickfont=dict(color=INK_2), title_font=dict(color=INK_2))
    return fig


def breakdown_chart(you_kg: dict, avg_t: dict, ranges_kg: dict):
    """Horizontal bars per category: your footprint vs the India profile.

    Error whiskers show the factor-uncertainty range on your bars.
    """
    cats = [c for c in you_kg if you_kg[c] > 0 or avg_t.get(c, 0) > 0]
    cats.sort(key=lambda c: you_kg[c])            # biggest at the top
    you = [you_kg[c] / 1000 for c in cats]
    lo = [(you_kg[c] - ranges_kg[c][0]) / 1000 for c in cats]
    hi = [(ranges_kg[c][2] - you_kg[c]) / 1000 for c in cats]
    avg = [avg_t.get(c, 0) for c in cats]

    fig = go.Figure()
    fig.add_bar(
        y=cats, x=avg, orientation="h", name="Typical urban Indian",
        marker_color=GREY,
        hovertemplate="%{y}<br>Typical: %{x:.2f} t/yr<extra></extra>",
    )
    fig.add_bar(
        y=cats, x=you, orientation="h", name="You",
        marker_color=BLUE,
        error_x=dict(type="data", array=hi, arrayminus=lo, color=INK_2,
                     thickness=1.2, width=4),
        customdata=[[ranges_kg[c][0] / 1000, ranges_kg[c][2] / 1000] for c in cats],
        hovertemplate=("%{y}<br>You: %{x:.2f} t/yr"
                       "<br>Likely range: %{customdata[0]:.2f}–%{customdata[1]:.2f} t"
                       "<extra></extra>"),
    )
    fig.update_layout(barmode="group", legend_traceorder="reversed")
    return _layout(fig, height=90 + 46 * len(cats), x_title="tonnes CO₂e per year")


def before_after_chart(before_kg: dict, after_kg: dict):
    """Only the categories the plan changes — unchanged pairs are just noise."""
    cats = [c for c in before_kg if after_kg.get(c, 0) < before_kg[c] - 1e-9]
    cats.sort(key=lambda c: before_kg[c])
    fig = go.Figure()
    fig.add_bar(
        y=cats, x=[before_kg[c] / 1000 for c in cats], orientation="h",
        name="Now", marker_color=GREY,
        hovertemplate="%{y}<br>Now: %{x:.2f} t/yr<extra></extra>",
    )
    fig.add_bar(
        y=cats, x=[after_kg[c] / 1000 for c in cats], orientation="h",
        name="With this plan", marker_color=BLUE,
        customdata=[(before_kg[c] - after_kg[c]) / 1000 for c in cats],
        hovertemplate=("%{y}<br>With plan: %{x:.2f} t/yr"
                       "<br>Saves %{customdata:.2f} t/yr<extra></extra>"),
    )
    fig.update_layout(barmode="group", legend_traceorder="reversed")
    return _layout(fig, height=90 + 50 * max(1, len(cats)), x_title="tonnes CO₂e per year")


def frontier_chart(optimal: list, greedy: list, marker_budget: float = None):
    """Best achievable saving vs budget, for the exact solver and for greedy.

    The gap between the lines is exactly what greedy loses by never
    reconsidering a choice. Where the lines touch, greedy happened to be
    optimal.
    """
    fig = go.Figure()
    fig.add_scatter(
        x=[b for b, _ in greedy], y=[kg / 1000 for _, kg in greedy],
        mode="lines", name="Greedy (best value-per-rupee first)",
        line=dict(color=ORANGE, width=2, shape="hv"),
        hovertemplate="Budget ₹%{x:,.0f}<br>Greedy saves %{y:.2f} t/yr<extra></extra>",
    )
    fig.add_scatter(
        x=[b for b, _ in optimal], y=[kg / 1000 for _, kg in optimal],
        mode="lines", name="Optimal (dynamic programming)",
        line=dict(color=BLUE, width=2, shape="hv"),
        hovertemplate="Budget ₹%{x:,.0f}<br>Optimal saves %{y:.2f} t/yr<extra></extra>",
    )
    if marker_budget is not None:
        fig.add_vline(x=marker_budget, line_width=1, line_color=MUTED)
        fig.add_annotation(x=marker_budget, y=0.02, yref="paper", text="your budget",
                           showarrow=False, xanchor="left", yanchor="bottom",
                           xshift=4, font=dict(color=MUTED, size=12))
    fig.update_layout(hovermode="x unified", legend_traceorder="reversed")
    fig.update_xaxes(tickprefix="₹", tickformat=",.0f")
    return _layout(fig, height=340, x_title="Annual budget",
                   y_title="CO₂e saved (t/yr)")
