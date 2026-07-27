"""Pattern management — list, create, rename, clone.

Wraps :class:`toolshop.daw.client.DAWClient` calls for pattern operations.
"""

from __future__ import annotations

from typing import Any, Dict

from .client import DAWClient


def list_patterns(client: DAWClient) -> Dict[str, Any]:
    """List all patterns with index, name, and length."""
    return client.call("patterns.list")  # type: ignore[return-value]


def create_pattern(client: DAWClient, name: str = "") -> Dict[str, Any]:
    """Create a new pattern, optionally naming it."""
    return client.call("patterns.create", name=name)  # type: ignore[return-value]


def rename_pattern(client: DAWClient, index: int, name: str) -> Dict[str, Any]:
    """Rename an existing pattern by index."""
    return client.call(  # type: ignore[return-value]
        "patterns.rename", index=index, name=name
    )


def clone_pattern(client: DAWClient, index: int, name: str = "") -> Dict[str, Any]:
    """Clone an existing pattern, optionally naming the copy."""
    return client.call(  # type: ignore[return-value]
        "patterns.clone", index=index, name=name
    )
