"""Source registry — loads ``sources/registry.json`` (SPEC §2 frozen schema).

Stdlib-only on import so ``sources._common.polite_get`` can lazily pull
``politeness`` blocks without a cycle and without paying for ``requests``.

Key API:
- ``load(path=None)`` / ``list_sources()`` / ``get(source_id)``
- ``validate_row(row)`` -> list of schema problems (used by contract tests)
- ``corpus_dir(row)`` / ``corpus_root(row, data_dir=None)`` — dir layout §3.1
- ``require_fetchable(row)`` — raises ``FetchPolicyError`` for
  ``fetch_policy != 'auto'`` or adapter-less rows (SPEC §6.4)
- ``resolve_adapter(row)`` — import ``sources/<adapter>.py``
- ``check_env_gate(row)`` — raises ``EnvGateError`` when env_gate unset
- ``data_dir()`` — TOOLSHOP_DATA_DIR -> <repo>/data/toolshop (mirrors
  toolshop/paths.py without importing the package — F-B1)
"""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

REGISTRY_PATH = Path(__file__).resolve().parent / "registry.json"

#: Frozen enums (SPEC §1.1 / §1.2).
LICENSE_TIERS = {
    "pd", "cc0", "cc-by", "cc-by-sa", "cc-by-nc",
    "paid-rf", "uploader-terms", "study-only", "uncleared",
}
FETCH_POLICIES = {"auto", "catalog-only", "manual"}
RELEASE_OK_STATES = {"yes", "conditional", "no"}

_REQUIRED_FIELDS = (
    "id", "name", "base_url", "license_tier", "fetch_policy",
    "adapter", "corpus_tag", "license_ref_default",
)


class FetchPolicyError(RuntimeError):
    """Raised when a fetch is attempted on a catalog-only/manual/registry-only
    source. The registry row exists for cataloging/metadata only (SPEC §1.2)."""


# ---------------------------------------------------------------------------
# Paths (mirrors toolshop/paths.py — do NOT import toolshop here)
# ---------------------------------------------------------------------------


def data_dir() -> Path:
    """Return the toolshop data directory (TOOLSHOP_DATA_DIR or
    ``<repo>/data/toolshop``). Absolute, even when the env var is relative."""
    raw = os.environ.get("TOOLSHOP_DATA_DIR")
    if raw:
        return Path(raw).expanduser().resolve()
    return Path(__file__).resolve().parents[2] / "data" / "toolshop"


def lyrics_root(data_dir_override: Optional[Path] = None) -> Path:
    return (Path(data_dir_override) if data_dir_override else data_dir()) / "lyrics"


# ---------------------------------------------------------------------------
# Registry loading
# ---------------------------------------------------------------------------

_cache: Dict[str, Any] = {}


def load(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load the registry doc (``{version, sources: [...], cut: [...]}``)."""
    path = Path(path) if path else REGISTRY_PATH
    key = str(path)
    if key not in _cache:
        doc = json.loads(path.read_text(encoding="utf-8"))
        _cache[key] = doc
    return _cache[key]


def list_sources(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    return load(path).get("sources", [])


def list_cut(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    return load(path).get("cut", [])


def get(source_id: str, path: Optional[Path] = None) -> Dict[str, Any]:
    """Return the registry row for ``source_id``; KeyError with a clear
    message listing known ids when absent."""
    for row in list_sources(path):
        if row.get("id") == source_id:
            return row
    known = ", ".join(sorted(r.get("id", "?") for r in list_sources(path)))
    raise KeyError(
        f"unknown source id '{source_id}' — known: {known} "
        f"(registry: {path or REGISTRY_PATH})"
    )


def validate_row(row: Dict[str, Any]) -> List[str]:
    """Return a list of schema problems; empty list means the row conforms
    to the SPEC §2 frozen schema."""
    problems: List[str] = []
    rid = row.get("id", "?")
    for f in _REQUIRED_FIELDS:
        if f not in row:
            problems.append(f"{rid}: missing required field '{f}'")
    tier = row.get("license_tier")
    if tier is not None and tier not in LICENSE_TIERS:
        problems.append(f"{rid}: license_tier '{tier}' not in enum {sorted(LICENSE_TIERS)}")
    pol = row.get("fetch_policy")
    if pol is not None and pol not in FETCH_POLICIES:
        problems.append(f"{rid}: fetch_policy '{pol}' not in enum {sorted(FETCH_POLICIES)}")
    # corpus_dir must equal corpus_tag unless explicitly overridden (genius is
    # the one sanctioned legacy exception — SPEC §2.1).
    cdir = row.get("corpus_dir")
    if cdir is not None and cdir != row.get("corpus_tag") and rid != "genius":
        problems.append(f"{rid}: corpus_dir '{cdir}' != corpus_tag '{row.get('corpus_tag')}'")
    # fetch_policy implications (SPEC §1.2/§2.1):
    if pol == "manual" and row.get("adapter") and rid != "looperman":
        problems.append(f"{rid}: manual sources ship no fetching adapter")
    return problems


def validate(path: Optional[Path] = None) -> List[str]:
    problems: List[str] = []
    seen = set()
    for row in list_sources(path):
        rid = row.get("id")
        if rid in seen:
            problems.append(f"duplicate source id '{rid}'")
        seen.add(rid)
        problems.extend(validate_row(row))
    return problems


# ---------------------------------------------------------------------------
# Corpus path resolution
# ---------------------------------------------------------------------------


def corpus_dir(row: Dict[str, Any]) -> Optional[str]:
    """On-disk corpus dir: ``corpus_dir`` override else ``corpus_tag``
    (SPEC §3.1 — genius is the only row where they differ)."""
    return row.get("corpus_dir") or row.get("corpus_tag")


def corpus_root(row: Dict[str, Any], data_dir_override: Optional[Path] = None) -> Optional[Path]:
    """``<data>/lyrics/<corpus_dir>`` for the row, or None for rows with no
    lyric corpus (paid packs — ``corpus_tag: null``)."""
    cdir = corpus_dir(row)
    if not cdir:
        return None
    return lyrics_root(data_dir_override) / cdir


# ---------------------------------------------------------------------------
# Fetch policy + adapter resolution
# ---------------------------------------------------------------------------


def is_fetchable(row: Dict[str, Any]) -> bool:
    return row.get("fetch_policy") == "auto" and bool(row.get("adapter"))


def require_fetchable(row: Dict[str, Any]) -> Dict[str, Any]:
    """Raise ``FetchPolicyError`` unless lyric fetching is permitted.

    This is the dispatcher-side enforcement of SPEC §1.2: catalog-only and
    manual sources (and registry rows with ``adapter: null``) have no fetch
    path — calling fetch on them is a clear error, never a silent no-op.
    """
    rid = row.get("id", "?")
    pol = row.get("fetch_policy")
    if pol != "auto":
        raise FetchPolicyError(
            f"source '{rid}' has fetch_policy '{pol}' — lyric fetching is "
            f"not permitted for this source (SPEC §1.2). "
            f"Use --catalog-only for catalog listing."
        )
    if not row.get("adapter"):
        raise FetchPolicyError(
            f"source '{rid}' has adapter=null — it is a registry row only; "
            f"there is no fetch path (SPEC §2.1)."
        )
    return row


def check_env_gate(row: Dict[str, Any]) -> None:
    """Raise ``EnvGateError`` when the row's ``env_gate`` var is unset
    (jamendo ships inert until JAMENDO_CLIENT_ID exists — GATE R)."""
    gate = row.get("env_gate")
    if gate and not os.environ.get(gate):
        # Lazy import keeps this module stdlib-only at import time.
        try:
            from ._common import EnvGateError
        except ImportError:
            from _common import EnvGateError  # type: ignore
        raise EnvGateError(gate, source_id=row.get("id", "?"))


def resolve_adapter(row: Dict[str, Any]):
    """Import and return the ``sources/<adapter>.py`` module for a row.

    Raises ``FetchPolicyError`` for adapter-less rows and a clear
    ``ModuleNotFoundError``-wrapped RuntimeError when the module is named but
    not yet implemented (adapter waves land after W1)."""
    rid = row.get("id", "?")
    name = row.get("adapter")
    if not name:
        raise FetchPolicyError(
            f"source '{rid}' has no adapter module (registry row only, SPEC §2.1)"
        )
    try:
        return importlib.import_module(f"sources.{name}")
    except ImportError as e1:
        try:
            return importlib.import_module(name)  # sources/ on sys.path directly
        except ImportError:
            raise RuntimeError(
                f"adapter 'sources/{name}.py' for source '{rid}' is named in "
                f"registry.json but not implemented yet (adapter wave WA): {e1}"
            ) from e1
