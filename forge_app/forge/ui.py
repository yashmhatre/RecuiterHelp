"""Small HTML building blocks for the FORGE AI interface.

Streamlit draws widgets; everything else on the dashboard (stat tiles, progress rings, the
funnel, list rows) is plain HTML passed to ``st.markdown``. Keeping those pieces here, as pure
functions returning strings, means app.py reads as layout rather than markup, and the pieces
can be tested without a running Streamlit server.

Two rules every function here follows:

* **One line of output.** Markdown treats an indented line as a code block, so a pretty-printed
  HTML snippet renders as literal tags. Every helper joins its parts with no newlines.
* **Escape what came from a person.** Names, companies and job titles are user or generated
  data; anything interpolated into markup goes through ``html.escape``.

Icons are inline SVG from the Lucide set (ISC licence), drawn at a 24px grid with a 2px stroke.
The UI/UX skill's checklist rules out emoji as icons -- they render differently on every
platform and read badly aloud -- and inline SVG needs no network request.
"""

from __future__ import annotations

import hashlib
from html import escape

# ---------------------------------------------------------------------------
# Icons
# ---------------------------------------------------------------------------

_ICON_PATHS: dict[str, str] = {
    "briefcase": '<path d="M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>'
                 '<rect width="20" height="14" x="2" y="6" rx="2"/>',
    "file-check": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>'
                  '<path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="m9 15 2 2 4-4"/>',
    "file-text": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>'
                 '<path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/>'
                 '<path d="M16 17H8"/>',
    "user": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "user-check": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>'
                  '<circle cx="9" cy="7" r="4"/><polyline points="16 11 18 13 22 9"/>',
    "eye": '<path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 '
           '.696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/>',
    "flame": '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 '
             '2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 '
             '1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
    "calendar-check": '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4"/>'
                      '<path d="M8 2v4"/><path d="M3 10h18"/><path d="m9 16 2 2 4-4"/>',
    "megaphone": '<path d="m3 11 18-5v12L3 14v-3z"/><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6"/>',
    "sparkles": '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 '
                '9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 '
                '15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 '
                '1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/>',
    "pen-square": '<path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>'
                  '<path d="M18.375 2.625a1 1 0 0 1 3 3l-9.013 9.014a2 2 0 0 1-.853.505l-2.873'
                  '.84a.5.5 0 0 1-.62-.62l.84-2.873a2 2 0 0 1 .506-.852z"/>',
    "heart": '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5'
             '-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>',
    "trending-up": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>'
                   '<polyline points="16 7 22 7 22 13"/>',
    "arrow-up": '<path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>',
    "graduation-cap": '<path d="M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 '
                      '0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z"/>'
                      '<path d="M22 10v6"/><path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/>'
              '<circle cx="12" cy="12" r="2"/>',
}


def icon(name: str, size: int = 20, color: str = "currentColor", stroke: float = 2) -> str:
    """An inline Lucide icon. Decorative by default: the text beside it carries the meaning."""
    paths = _ICON_PATHS.get(name, _ICON_PATHS["sparkles"])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{stroke}" '
        f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
        f"{paths}</svg>"
    )


# ---------------------------------------------------------------------------
# Tones: one tinted surface and one strong colour per stat family
# ---------------------------------------------------------------------------

#: (surface tint, icon tile, icon colour). Icon colours are decorative, never text, so they are
#: free of the 4.5:1 rule; text on these tints uses the ink colours, which pass on all of them.
TONES: dict[str, tuple[str, str, str]] = {
    "indigo": ("#F3F2FF", "#E6E3FF", "#5B4CF2"),
    "green": ("#EEFAF2", "#D9F3E2", "#178841"),
    "violet": ("#F6F1FF", "#ECE2FF", "#7C3AED"),
    "amber": ("#FFF7EC", "#FFEBCF", "#C26A05"),
    "blue": ("#EFF5FF", "#DCE8FF", "#2563EB"),
    "rose": ("#FFF1F2", "#FFE0E3", "#E11D48"),
}


def _tone(name: str) -> tuple[str, str, str]:
    return TONES.get(name, TONES["indigo"])


def icon_tile(name: str, tone: str = "indigo", size: int = 44) -> str:
    _, tile, ink = _tone(tone)
    return (
        f'<div class="fx-tile" style="width:{size}px;height:{size}px;background:{tile};'
        f'color:{ink};">{icon(name, size=int(size * 0.5))}</div>'
    )


# ---------------------------------------------------------------------------
# Stat cards
# ---------------------------------------------------------------------------


def stat_card(label: str, value: str, foot: str, icon_name: str, tone: str,
              unit: str = "", trend_up: bool = False) -> str:
    """One of the five tinted tiles across the top of the dashboard."""
    surface, _, _ = _tone(tone)
    unit_html = f'<span class="fx-stat-unit">{escape(unit)}</span>' if unit else ""
    arrow = icon("arrow-up", size=13, color="#178841", stroke=2.4) if trend_up else ""
    foot_cls = "fx-stat-foot fx-up" if trend_up else "fx-stat-foot"
    return (
        f'<div class="fx-stat" style="background:{surface};">'
        f"{icon_tile(icon_name, tone)}"
        f'<div class="fx-stat-body"><div class="fx-stat-label">{escape(label)}</div>'
        f'<div class="fx-stat-value">{escape(str(value))}{unit_html}</div>'
        f'<div class="{foot_cls}">{arrow}<span>{escape(foot)}</span></div></div></div>'
    )


# ---------------------------------------------------------------------------
# Rings and charts
# ---------------------------------------------------------------------------


def ring(fraction: float, size: int = 96, stroke: int = 9, color: str = "#5B4CF2",
         track: str = "#E9E8F5", center: str = "", label: str = "") -> str:
    """A progress ring drawn in SVG, with arbitrary HTML centred inside it.

    ``label`` is the accessible name; the ring itself is an image of a number, so a screen
    reader needs the number said in words.
    """
    fraction = max(0.0, min(1.0, float(fraction)))
    r = (size - stroke) / 2
    circumference = 2 * 3.141592653589793 * r
    dash = circumference * fraction
    aria = f' role="img" aria-label="{escape(label)}"' if label else ' aria-hidden="true"'
    return (
        f'<div class="fx-ring" style="width:{size}px;height:{size}px;"{aria}>'
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" aria-hidden="true">'
        f'<circle cx="{size / 2}" cy="{size / 2}" r="{r}" fill="none" stroke="{track}" '
        f'stroke-width="{stroke}"/>'
        f'<circle cx="{size / 2}" cy="{size / 2}" r="{r}" fill="none" stroke="{color}" '
        f'stroke-width="{stroke}" stroke-linecap="round" '
        f'stroke-dasharray="{dash:.2f} {circumference:.2f}" '
        f'transform="rotate(-90 {size / 2} {size / 2})"/></svg>'
        f'<div class="fx-ring-center">{center}</div></div>'
    )


def sparkline(values: list[float], width: int = 200, height: int = 72,
              color: str = "#5B4CF2") -> str:
    """A small line chart with a point on each value, scaled to its own range."""
    if not values:
        return ""
    pad = 6
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    step = (width - 2 * pad) / max(1, len(values) - 1)
    pts = [
        (pad + i * step, height - pad - (v - lo) / span * (height - 2 * pad))
        for i, v in enumerate(values)
    ]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{pad},{height - pad} {line} {pts[-1][0]:.1f},{height - pad}"
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#fff" stroke="{color}" stroke-width="2"/>'
        for x, y in pts
    )
    return (
        f'<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" '
        f'aria-hidden="true">'
        f'<polygon points="{area}" fill="{color}" fill-opacity="0.08"/>'
        f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="2.2" '
        f'stroke-linejoin="round" stroke-linecap="round"/>{dots}</svg>'
    )


def progress_bar(label: str, pct: int, color: str) -> str:
    pct = max(0, min(100, int(pct)))
    return (
        f'<div class="fx-progress" role="img" aria-label="{escape(label)}: {pct}%">'
        f'<span class="fx-progress-label">{escape(label)}</span>'
        f'<span class="fx-progress-track"><span class="fx-progress-fill" '
        f'style="width:{pct}%;background:{color};"></span></span>'
        f'<span class="fx-progress-pct">{pct}%</span></div>'
    )


# ---------------------------------------------------------------------------
# Rows
# ---------------------------------------------------------------------------

_LOGO_COLOURS = ("#5B4CF2", "#0F766E", "#B45309", "#BE185D", "#1D4ED8", "#7C3AED", "#15803D")


def logo_tile(company: str, size: int = 48) -> str:
    """A company initial on a colour picked from its name, so it is stable across reruns."""
    digest = int(hashlib.md5(company.encode("utf-8")).hexdigest(), 16)
    colour = _LOGO_COLOURS[digest % len(_LOGO_COLOURS)]
    initial = escape((company.strip()[:1] or "?").upper())
    return (
        f'<div class="fx-logo" style="width:{size}px;height:{size}px;background:{colour};" '
        f'aria-hidden="true">{initial}</div>'
    )


def posted_ago(days: int) -> str:
    if days <= 0:
        return "Today"
    if days == 1:
        return "1d ago"
    if days < 7:
        return f"{days}d ago"
    weeks = days // 7
    return f"{weeks}w ago"


def initials(name: str) -> str:
    parts = [p for p in name.split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def avatar(name: str, size: int = 40) -> str:
    return (
        f'<div class="fx-avatar" style="width:{size}px;height:{size}px;" aria-hidden="true">'
        f"{escape(initials(name))}</div>"
    )
