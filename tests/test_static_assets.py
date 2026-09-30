"""The front-end files must at least parse.

This exists because of a real failure. A text edit left
``await window.refreshGmail = refreshGmail;`` in ``gmail.js``, which is a syntax error, so the
browser refused the whole file and *no* event listener attached. The symptom reported was "the
Connect button isn't clickable" — nothing in the Python test suite could have caught it, and the
server happily served the broken file with HTTP 200.

Anything that ships to a browser gets checked here now.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parent.parent / "prototype" / "static"
SCRIPTS = sorted(STATIC.glob("*.js"))
PAGES = sorted(STATIC.glob("*.html"))

node = shutil.which("node")


def test_there_are_scripts_to_check():
    """A glob that silently matches nothing would make every test below vacuous."""
    assert SCRIPTS, f"no .js files found in {STATIC}"


@pytest.mark.skipif(not node, reason="node is not installed; syntax cannot be checked")
@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_script_parses(script: Path):
    result = subprocess.run(
        [node, "--check", str(script)], capture_output=True, text=True, timeout=30
    )

    assert result.returncode == 0, f"{script.name} does not parse:\n{result.stderr}"


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_no_mangled_assignment_to_a_call(script: Path):
    """Guards the exact shape of the bug, so it fails even where node is unavailable."""
    source = script.read_text(encoding="utf-8")

    assert "await window." not in source or "= " not in source.split("await window.")[1][:60], (
        f"{script.name} looks like a botched text replacement around 'await window.'"
    )


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_every_script_the_page_loads_exists(page: Path):
    """A typo'd src is a 404 the page ignores in silence."""
    import re

    html = page.read_text(encoding="utf-8")
    for src in re.findall(r'<script[^>]+src="/static/([^"?]+)', html):
        assert (STATIC / src).is_file(), f"{page.name} loads /static/{src}, which is missing"


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_every_tab_button_has_a_matching_section(page: Path):
    """The nav and the sections are edited separately; a mismatch hides a whole tab."""
    import re

    html = page.read_text(encoding="utf-8")
    tabs = set(re.findall(r'data-tab="([^"]+)"', html))
    sections = set(re.findall(r'id="tab-([^"]+)"', html))

    assert tabs, "no tab buttons found"
    assert tabs == sections, f"tabs {sorted(tabs)} do not match sections {sorted(sections)}"


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_ids_are_unique(page: Path):
    """Two elements sharing an id means getElementById silently returns the wrong one."""
    import re
    from collections import Counter

    html = page.read_text(encoding="utf-8")
    counts = Counter(re.findall(r'\sid="([^"]+)"', html))
    duplicates = [name for name, n in counts.items() if n > 1]

    assert not duplicates, f"duplicate ids in {page.name}: {duplicates}"
