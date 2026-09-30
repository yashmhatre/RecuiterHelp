"""Provider lookup by name, imported lazily.

Lazy on purpose. The Gmail and Graph clients pull in large, unrelated dependency trees
(``google-api-python-client``, ``msal``), and only one provider is ever configured for a given
mailbox. Importing both eagerly would mean a machine running Outlook cannot start without the
Google libraries installed, and would make every pipeline test that touches the registry depend
on both SDKs.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from providers.base import BaseMailProvider

__all__ = ["KNOWN_PROVIDERS", "get_provider_class", "get_provider"]

#: name -> "module:ClassName". Resolved only when asked for.
KNOWN_PROVIDERS: dict[str, str] = {
    "gmail": "providers.gmail:GmailProvider",
    "outlook": "providers.outlook:OutlookProvider",
    "fake": "providers.fake:FakeMailProvider",
}


def get_provider_class(name: str) -> type[BaseMailProvider]:
    """Resolve a provider name to its class, importing only that provider's module."""
    key = (name or "").strip().lower()
    if key not in KNOWN_PROVIDERS:
        raise ValueError(
            f"Unknown provider {name!r}. Known providers: {', '.join(sorted(KNOWN_PROVIDERS))}"
        )

    module_path, class_name = KNOWN_PROVIDERS[key].split(":")
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise ImportError(
            f"Provider {key!r} is not available: {exc}. Install its dependencies with "
            f"pip install -e '.[providers]'"
        ) from exc

    return getattr(module, class_name)


def get_provider(name: str, **kwargs: object) -> BaseMailProvider:
    """Construct the named provider. Keyword arguments are passed to its constructor."""
    return get_provider_class(name)(**kwargs)  # type: ignore[arg-type]
