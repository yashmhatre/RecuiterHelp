"""Repo-wide guard: no code path can send an email.

Requirement 5 says the agent saves drafts and a human sends every one. That is enforced in three
independent places, so no single mistake defeats it:

1. The OAuth app registration grants no send permission (P0-05).
2. ``MailProvider`` and ``BaseMailProvider`` declare no send method (P2-01).
3. This test, which scans every Python file in the repository.

Why AST and not grep
--------------------
``grep -r "\\.send("`` cannot tell code from prose. ``docs/CONTRACTS.md``, the tickets, and
several comments all *discuss* sending, and P0-05 must contain the literal strings
``"Mail.Send"`` and ``"gmail.send"`` in order to reject those scopes. A text scan would either
fire on all of that or be watered down until it caught nothing. Parsing means only real calls
and real string literals are considered.

Deliberate exception
--------------------
A line carrying the marker ``send-guard: allow`` is skipped. P0-05's scope-rejection code needs
it, since refusing a send scope means naming it. Every use has to be visible in review, which is
the point: the guard is not silently suppressible across a file or the whole run.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Directories holding Python that runs against a real mailbox.
SCANNED_DIRS = ("email_agent", "providers", "pipeline", "profiles", "eval", "scripts")

#: Scanned as well, since main.py sits at the root.
SCANNED_FILES = ("main.py",)

#: This file, and the contract suite, name the forbidden things in order to assert their absence.
EXEMPT_FILES = {"test_no_send_path.py"}

ALLOW_MARKER = "send-guard: allow"

#: Method names that would send mail on any of the providers in play.
FORBIDDEN_CALL_NAMES = frozenset(
    {
        "send",
        "send_mail",
        "sendMail",
        "send_message",
        "send_draft",
        "sendmail",
    }
)

#: Substrings that, inside a string literal, mean a send scope or a send endpoint.
FORBIDDEN_LITERALS = (
    "mail.send",  # Graph application permission
    "gmail.send",  # Gmail OAuth scope
    "/sendmail",  # Graph endpoint
    "messages/send",  # Graph endpoint
    "drafts/send",  # Gmail endpoint
    "messages.send",  # google-api-python-client method chain
    "https://mail.google.com/",  # full-access Gmail scope; includes send
)


def python_files() -> list[Path]:
    """Every Python file this guard covers."""
    found: list[Path] = []
    for directory in SCANNED_DIRS:
        base = REPO_ROOT / directory
        if base.is_dir():
            found.extend(p for p in base.rglob("*.py") if p.name not in EXEMPT_FILES)
    for name in SCANNED_FILES:
        path = REPO_ROOT / name
        if path.is_file():
            found.append(path)
    # Tests are scanned too: a test helper that sends is still a send path.
    tests = REPO_ROOT / "tests"
    if tests.is_dir():
        found.extend(p for p in tests.rglob("*.py") if p.name not in EXEMPT_FILES)
    return sorted(set(found))


def _allowed_lines(source: str) -> set[int]:
    return {
        number
        for number, line in enumerate(source.splitlines(), start=1)
        if ALLOW_MARKER in line
    }


def find_send_paths(source: str, filename: str = "<string>") -> list[str]:
    """Return a description of every send path in ``source``.

    Two kinds are detected: a call to a send-shaped method, and a string literal naming a send
    scope or endpoint.
    """
    violations: list[str] = []

    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        return [f"{filename}: could not parse ({exc})"]

    allowed = _allowed_lines(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = None
            if isinstance(node.func, ast.Attribute):
                name = node.func.attr
            elif isinstance(node.func, ast.Name):
                name = node.func.id
            if name in FORBIDDEN_CALL_NAMES and node.lineno not in allowed:
                violations.append(f"{filename}:{node.lineno}: call to {name}()")

        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            lowered = node.value.lower()
            for needle in FORBIDDEN_LITERALS:
                if needle in lowered and node.lineno not in allowed:
                    violations.append(
                        f"{filename}:{node.lineno}: string literal contains {needle!r}"
                    )
                    break

        # A function or method whose own name is send-shaped.
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if node.name in FORBIDDEN_CALL_NAMES and node.lineno not in allowed:
                violations.append(f"{filename}:{node.lineno}: defines {node.name}()")

    return violations


# ---------------------------------------------------------------------------
# The guard itself
# ---------------------------------------------------------------------------


def test_no_send_path_anywhere_in_the_repository():
    """The headline assertion. If this fails, the agent can send mail."""
    all_violations: list[str] = []

    for path in python_files():
        source = path.read_text(encoding="utf-8")
        relative = path.relative_to(REPO_ROOT).as_posix()
        all_violations.extend(find_send_paths(source, relative))

    assert not all_violations, "Send path(s) found:\n  " + "\n  ".join(all_violations)


def test_the_guard_actually_scans_something():
    """A guard that silently covers zero files would pass forever."""
    files = python_files()

    assert len(files) >= 8, f"only scanned {len(files)} files"
    names = {p.name for p in files}
    assert "contracts.py" in names
    assert "fake.py" in names


# ---------------------------------------------------------------------------
# Proof the guard works, per the ticket's acceptance criterion
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "snippet",
    [
        "service.users().messages().send(userId='me', body=b)",
        "client.send_mail(message)",
        "provider.send(draft)",
        "await graph.sendMail(payload)",
        "smtp.sendmail(sender, to, body)",
    ],
)
def test_guard_catches_a_send_call(snippet: str):
    assert find_send_paths(snippet, "probe.py")


@pytest.mark.parametrize(
    "snippet",
    [
        'SCOPES = ["https://www.googleapis.com/auth/gmail.send"]',
        'PERMISSIONS = ["Mail.Send"]',
        'url = "/me/sendMail"',
        'endpoint = "v1.0/me/messages/send"',
        'SCOPES = ["https://mail.google.com/"]',
    ],
)
def test_guard_catches_a_send_scope_or_endpoint(snippet: str):
    assert find_send_paths(snippet, "probe.py")


def test_guard_catches_a_method_named_send():
    snippet = "class P:\n    def send(self, content):\n        pass\n"

    assert find_send_paths(snippet, "probe.py")


@pytest.mark.parametrize(
    "snippet",
    [
        "# never call provider.send(draft)",
        '"""This module must not send. Do not add send_mail()."""',
        "provider.save_draft(content)",
        'SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]',
        'PERMISSIONS = ["Mail.ReadWrite"]',
        "resend_count = 0",
        "descendants = []",
    ],
)
def test_guard_does_not_fire_on_prose_or_legitimate_code(snippet: str):
    """A guard with false positives gets disabled, and then protects nothing."""
    assert find_send_paths(snippet, "probe.py") == []


def test_the_allow_marker_is_respected_for_scope_rejection():
    """P0-05 must name the forbidden scopes in order to refuse them."""
    snippet = 'FORBIDDEN = ["Mail.Send", "gmail.send"]  # send-guard: allow (rejecting these)\n'

    assert find_send_paths(snippet, "probe.py") == []


def test_the_allow_marker_only_covers_its_own_line():
    """Not suppressible file-wide, so every exception stays visible in review."""
    snippet = (
        'ok = ["Mail.Send"]  # send-guard: allow\n'
        "provider.send(draft)\n"
    )
    violations = find_send_paths(snippet, "probe.py")

    assert len(violations) == 1
    assert ":2:" in violations[0]


def test_contracts_mail_provider_has_no_send_member():
    from email_agent.contracts import MailProvider

    assert not any("send" in name.lower() for name in vars(MailProvider))


def test_base_provider_has_no_send_member():
    from providers.base import BaseMailProvider

    members = [n for n in vars(BaseMailProvider) if n != "_FORBIDDEN_SUBCLASS_ATTRS"]

    assert not any("send" in name.lower() for name in members)
