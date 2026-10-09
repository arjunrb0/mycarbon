"""
Shared visual components.

Styling targets only this module's own class names (prefixed `mc-`), never
Streamlit's internal CSS classes — those change between Streamlit releases and
would silently break the design on the next upgrade.
"""

import html

import streamlit as st

CSS = """
<style>
.block-container { padding-top: 4.6rem; max-width: 1240px; }

.mc-hero {
  background: linear-gradient(135deg, #123f2a 0%, #1f7a4d 55%, #2f9a68 100%);
  border-radius: 18px; padding: 34px 32px 30px; margin-bottom: 18px; color: #fff;
}
.mc-hero .mc-eyebrow {
  text-transform: uppercase; letter-spacing: .09em; font-size: .78rem;
  font-weight: 650; color: #bfe6cf; margin: 0 0 6px;
}
.mc-hero h1 {
  color: #fff; margin: 0; padding: 0; font-size: clamp(1.7rem, 3.4vw, 2.5rem);
  line-height: 1.15; font-weight: 750;
}
.mc-hero p.mc-sub { color: #dcf1e4; margin: 10px 0 0; font-size: 1.05rem; max-width: 760px; }

.mc-section { margin: 30px 0 6px; }
.mc-section h2 { font-size: 1.35rem; margin: 0; padding: 0; font-weight: 700; }
.mc-section p { color: #52514e; margin: 4px 0 0; font-size: .95rem; }

.mc-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
            gap: 12px; margin: 6px 0 4px; }
.mc-tiles.mc-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.mc-tile {
  background: #fff; border: 1px solid #e1e0d9; border-radius: 14px; padding: 14px 16px;
}
.mc-tile .mc-label { font-size: .8rem; color: #52514e; font-weight: 600; margin: 0; }
.mc-tile .mc-value { font-size: 1.65rem; font-weight: 750; color: #16201a;
                     margin: 2px 0 0; line-height: 1.15; }
.mc-tile .mc-note { font-size: .8rem; color: #6b6a65; margin: 4px 0 0; }
.mc-tile.mc-lead { border-color: #1f7a4d; box-shadow: 0 0 0 1px #1f7a4d inset; }
.mc-tile.mc-lead .mc-value { font-size: 2.1rem; color: #1f7a4d; }

.mc-badge { display: inline-block; font-size: .72rem; font-weight: 650;
            padding: 2px 8px; border-radius: 999px; border: 1px solid; white-space: nowrap; }
.mc-badge.HIGH   { color: #0f5132; background: #e6f4ea; border-color: #b7dfc4; }
.mc-badge.MEDIUM { color: #6b4e00; background: #fdf3d8; border-color: #efd99a; }
.mc-badge.LOW    { color: #7a2e12; background: #fbe9e2; border-color: #f0c2ae; }

.mc-empty { border: 1.5px dashed #c3c2b7; border-radius: 16px; padding: 30px 24px;
            text-align: center; color: #52514e; background: #fcfcfb; }
.mc-empty h3 { margin: 0 0 6px; color: #16201a; font-size: 1.15rem; }

.mc-step { display: flex; gap: 14px; padding: 12px 0; border-bottom: 1px solid #ecebe6; }
.mc-step:last-child { border-bottom: none; }
.mc-step .mc-num { flex: 0 0 30px; height: 30px; border-radius: 50%; background: #e3f1e8;
                   color: #1f7a4d; font-weight: 750; display: flex; align-items: center;
                   justify-content: center; }
.mc-step b { color: #16201a; }
.mc-step span { color: #52514e; font-size: .93rem; }

.mc-footer { text-align: center; color: #898781; font-size: .82rem; margin: 40px 0 10px; }
.mc-footer a { color: #1f7a4d; }

@media (max-width: 640px) {
  .mc-hero { padding: 24px 20px; border-radius: 14px; }
  .mc-tile .mc-value { font-size: 1.4rem; }
  .mc-tile.mc-lead .mc-value { font-size: 1.7rem; }
}
</style>
"""


def inject_css():
    st.html(CSS)


def hero(title: str, subtitle: str = "", eyebrow: str = ""):
    # scripts/keep_awake.py looks for the .mc-hero class to know the live app
    # is really running — keep it if you restyle this.
    st.html(
        f"<div class='mc-hero'>"
        + (f"<p class='mc-eyebrow'>{html.escape(eyebrow)}</p>" if eyebrow else "")
        + f"<h1>{html.escape(title)}</h1>"
        + (f"<p class='mc-sub'>{html.escape(subtitle)}</p>" if subtitle else "")
        + "</div>"
    )


def section(title: str, caption: str = ""):
    st.html(
        f"<div class='mc-section'><h2>{html.escape(title)}</h2>"
        + (f"<p>{html.escape(caption)}</p>" if caption else "")
        + "</div>"
    )


def tiles(items, columns=None):
    """A responsive row of stat tiles.

    items: list of (label, value, note, lead) tuples. The first "lead" tile is
    the hero number; the rest give it context. Values are escaped because they
    can include user-derived text.
    """
    cells = []
    for label, value, note, lead in items:
        cells.append(
            f"<div class='mc-tile{' mc-lead' if lead else ''}'>"
            f"<p class='mc-label'>{html.escape(label)}</p>"
            f"<p class='mc-value'>{html.escape(value)}</p>"
            + (f"<p class='mc-note'>{html.escape(note)}</p>" if note else "")
            + "</div>"
        )
    extra = f" mc-cols-{columns}" if columns else ""
    st.html(f"<div class='mc-tiles{extra}'>{''.join(cells)}</div>")


def badge_text(confidence: str) -> str:
    """Plain-text confidence label for tables, where HTML isn't rendered."""
    return {"HIGH": "● High", "MEDIUM": "◐ Medium", "LOW": "○ Low"}.get(confidence, "—")


def empty_state(title: str, body: str):
    st.html(f"<div class='mc-empty'><h3>{html.escape(title)}</h3>"
            f"<p>{html.escape(body)}</p></div>")


def steps(items):
    """Numbered explanation steps: list of (title, body)."""
    rows = "".join(
        f"<div class='mc-step'><div class='mc-num'>{i}</div>"
        f"<div><b>{html.escape(t)}</b><br><span>{html.escape(b)}</span></div></div>"
        for i, (t, b) in enumerate(items, 1)
    )
    st.html(f"<div>{rows}</div>")


def footer():
    st.html(
        "<div class='mc-footer'>MyCarbon · built by Arjun Reddy Bathula · "
        "<a href='https://github.com/arjunrb0/mycarbon'>source on GitHub</a></div>"
    )


def inr(amount: float) -> str:
    """Format rupees with Indian digit grouping: ₹1,50,000 rather than ₹150,000."""
    n = int(round(amount))
    sign, s = ("-" if n < 0 else ""), str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups) + "," + tail
    return f"{sign}₹{s}"
