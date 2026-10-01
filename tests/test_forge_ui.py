"""Tests for the FORGE AI dashboard building blocks in forge_app/forge/ui.py.

These are the pieces that go into ``st.markdown(..., unsafe_allow_html=True)``, so the two
things worth pinning are the ones that fail silently in a browser: markup that Markdown turns
into a code block, and user text that turns into markup.
"""

from __future__ import annotations

import re

import pytest

from forge_app.forge import navigation, ui


def test_every_helper_returns_a_single_line():
    """An indented second line is a Markdown code block: the tags would print as text."""
    pieces = [
        ui.icon("briefcase"),
        ui.stat_card("Jobs Found", "8", "4 this week", "briefcase", "indigo", trend_up=True),
        ui.ring(0.5, center="<b>50%</b>", label="half"),
        ui.sparkline([1, 3, 2, 5]),
        ui.progress_bar("Databricks", 58, "#178841"),
        ui.logo_tile("Acme"),
        ui.avatar("Gauri Joshi"),
        ui.icon_tile("eye", "amber"),
    ]
    for html in pieces:
        assert "\n" not in html


def test_people_supplied_text_is_escaped():
    hostile = '<img src=x onerror="alert(1)">'
    for html in (
        ui.stat_card(hostile, hostile, hostile, "eye", "blue", unit=hostile),
        ui.progress_bar(hostile, 10, "#000"),
        ui.logo_tile(hostile),
        ui.avatar(hostile),
        ui.ring(0.1, label=hostile),
    ):
        assert "<img" not in html


@pytest.mark.parametrize("fraction, expected", [(0, 0.0), (0.25, 0.25), (1, 1.0), (7, 1.0), (-1, 0.0)])
def test_the_ring_draws_the_fraction_it_is_given_clamped(fraction, expected):
    html = ui.ring(fraction, size=100, stroke=10)
    dash, circumference = map(float, re.search(r'stroke-dasharray="([\d.]+) ([\d.]+)"', html).groups())
    assert dash / circumference == pytest.approx(expected, abs=1e-3)


def test_a_ring_with_a_label_is_an_image_with_a_name_and_one_without_is_hidden():
    assert 'role="img" aria-label="Ready for 3 roles"' in ui.ring(0.3, label="Ready for 3 roles")
    assert 'aria-hidden="true"' in ui.ring(0.3).split(">")[0]


def test_progress_is_clamped_and_announced():
    assert "width:100%" in ui.progress_bar("x", 140, "#000")
    assert "width:0%" in ui.progress_bar("x", -5, "#000")
    assert 'aria-label="Python: 54%"' in ui.progress_bar("Python", 54, "#000")


def test_a_flat_sparkline_does_not_divide_by_zero():
    assert "<polyline" in ui.sparkline([0, 0, 0, 0])
    assert ui.sparkline([]) == ""


def test_a_company_keeps_its_logo_colour_across_reruns():
    assert ui.logo_tile("Vertex Cloud Partners") == ui.logo_tile("Vertex Cloud Partners")


@pytest.mark.parametrize("name, expected", [
    ("Gauri Joshi", "GJ"), ("Gauri", "GA"), ("  ", "?"), ("Anna Maria Lopez", "AL"),
])
def test_initials(name, expected):
    assert ui.initials(name) == expected


@pytest.mark.parametrize("days, expected", [(0, "Today"), (1, "1d ago"), (5, "5d ago"), (14, "2w ago")])
def test_posted_ago(days, expected):
    assert ui.posted_ago(days) == expected


def test_icons_are_decorative_and_unknown_names_still_render():
    assert 'aria-hidden="true"' in ui.icon("eye")
    assert "<svg" in ui.icon("no-such-icon")


@pytest.mark.parametrize("recruiter", [True, False])
def test_every_page_in_the_sidebar_has_its_own_icon(recruiter):
    """A page without one falls back to a chevron, which reads as a bug in a list of icons."""
    for entry in navigation.entries_for(recruiter):
        assert entry.key in navigation.ICONS, entry.key
        assert navigation.icon_for(entry.key).startswith(":material/")
