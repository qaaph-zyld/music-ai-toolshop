"""Looperman catalog adapter — ``fetch_policy='manual'`` (SPEC §6.3/§9).

HARD RULE — enforced by contract test (SPEC §7.2): this module contains
**ZERO network code**. No ``requests``/``urllib``/``http``/``socket``
imports, no URL constants, no fetch path. Looperman's Terms & Conditions
("Misuse And Abuse Of Services", looperman.com/help/terms) ban automated
extraction **and** ML training verbatim (R3 §1):

    "We strictly prohibit unauthorised access or downloading of data
    using any computer program including but not limited to downloaders,
    page scrapers, data mining, web scraping, and automated data
    extraction…"
    "…it is prohibited for anyone to use our content for the training or
    improvement of any algorithm…"

The only legal ingest path is a HUMAN copying browser-visible metadata
into a local export file; this module parses that file only.

Import sources, in precedence order:

1. explicit ``path=`` — a file or a directory of export files
2. drop-zone ``<data>/lyrics/looperman/_import/`` — ``*.json`` /
   ``*.jsonl`` / ``*.csv`` files the user drops in
3. the hand-maintained ``<data>/lyrics/looperman/_catalog.json`` itself
   (SPEC §9: rows already in catalog shape are re-emitted — fid-keyed
   dedup makes the round-trip idempotent)

Export row fields (only ``title`` required; alias names accepted):

    title, uploader|artist|creator|user, bpm, key, genre,
    usage|usage_terms, date|upload_date, time_sig, duration_s,
    vocal_sex, vocal_type, autotune, adult, has_lyrics,
    id|foreign_identifier|url

FREE-TEXT FIELDS ARE REFUSED: ``description`` / ``lyrics`` / ``comment``
/ ``notes`` are dropped at parse time — uploader-authored text is
uploader © and ToS-protected (R3 §1); it must never enter the catalog.
``has_lyrics`` (the site's structured tag) is kept as a boolean flag —
the lyric text itself is never stored.

Emitted rows are **plain dicts** in ``CatalogEntry.to_dict()`` shape, NOT
``CatalogEntry`` objects: importing ``sources._common`` would pull
``requests`` into this module's import graph (``_common`` provides
``polite_get``). The dispatcher's ``upsert_entries`` accepts dicts
verbatim, so serialized catalog rows are identical either way.
"""

from __future__ import annotations

import csv
import json
import zlib
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

try:
    from . import registry as _registry
except ImportError:  # sources/ dir directly on sys.path
    try:
        import registry as _registry  # type: ignore
    except ImportError:
        _registry = None  # type: ignore

SOURCE_ID = "looperman"
CORPUS_DIRNAME = "looperman"
DROPZONE_NAME = "_import"
CATALOG_NAME = "_catalog.json"
_EXPORT_GLOBS = ("*.json", "*.jsonl", "*.csv")

# Field aliases accepted in user exports (browser-visible metadata, R3 §1).
_ALIASES: Dict[str, tuple] = {
    "title": ("title", "name", "track", "track_title"),
    "uploader": ("uploader", "artist", "creator", "user", "username",
                 "uploaded_by", "author"),
    "bpm": ("bpm", "tempo"),
    "key": ("key", "musical_key", "song_key"),
    "genre": ("genre", "style_genre"),
    "usage": ("usage", "usage_terms", "license_terms", "terms", "licence"),
    "upload_date": ("upload_date", "date", "uploaded", "added", "created"),
    "time_sig": ("time_sig", "timesig", "time_signature"),
    "duration_s": ("duration_s", "duration", "length_s", "secs", "seconds"),
    "vocal_sex": ("vocal_sex", "sex", "male_female", "gender"),
    "vocal_type": ("vocal_type", "type", "vocal_style", "part"),
    "autotune": ("autotune", "auto_tune"),
    "adult": ("adult", "adult_content", "explicit"),
    "has_lyrics": ("has_lyrics", "haslyrics", "lyrics_tag"),
    "fid": ("foreign_identifier", "id", "looperman_id", "track_id",
            "acapella_id", "external_id"),
    "url": ("url", "link", "source_url", "page", "page_url"),
}
#: Uploader-authored free text — dropped unconditionally (ToS-protected ©).
_REFUSED_KEYS = {"description", "lyrics", "lyric", "comment", "comments",
                 "notes", "note", "desc", "about", "bio"}
#: meta keys copied from export rows (whitelist — nothing else propagates).
_META_KEYS = ("bpm", "key", "genre", "usage", "upload_date", "time_sig",
              "duration_s", "vocal_sex", "vocal_type", "autotune", "adult",
              "has_lyrics")
_TRUE_VALUES = {"1", "true", "yes", "y", "on", "male", "female", "tagged"}


# ---------------------------------------------------------------------------
# paths — resolved via sources.registry (stdlib-only, no network imports)
# ---------------------------------------------------------------------------


def _lyrics_root(data_dir: Optional[Path]) -> Path:
    if data_dir is not None:
        return Path(data_dir) / "lyrics"
    if _registry is not None:
        return _registry.lyrics_root()
    # last-resort mirror of registry.data_dir() (no registry on path)
    import os
    raw = os.environ.get("TOOLSHOP_DATA_DIR")
    if raw:
        return Path(raw).expanduser().resolve() / "lyrics"
    return Path(__file__).resolve().parents[2] / "data" / "toolshop" / "lyrics"


def _corpus_root(data_dir: Optional[Path]) -> Path:
    return _lyrics_root(data_dir) / CORPUS_DIRNAME


def dropzone_dir(data_dir: Optional[Path] = None) -> Path:
    """The hand-drop directory a user fills with export files."""
    return _corpus_root(data_dir) / DROPZONE_NAME


# ---------------------------------------------------------------------------
# export-file parsing
# ---------------------------------------------------------------------------


def _iter_json(path: Path) -> Iterator[Dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(doc, list):
        rows = doc
    elif isinstance(doc, dict):
        rows = doc.get("entries") or doc.get("items") or doc.get("acapellas") or []
    else:
        rows = []
    for r in rows:
        if isinstance(r, dict):
            yield r


def _iter_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            yield obj


def _iter_csv(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            yield {k: v for k, v in row.items() if k is not None}


def iter_export_file(path: Path) -> Iterator[Dict[str, Any]]:
    """Yield raw row dicts from one export file (.json/.jsonl/.csv)."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".json":
        yield from _iter_json(path)
    elif suffix == ".jsonl":
        yield from _iter_jsonl(path)
    elif suffix == ".csv":
        yield from _iter_csv(path)
    else:
        raise ValueError(f"unsupported export format: {path} "
                         f"(use .json / .jsonl / .csv)")


def _export_files(path: Optional[Path], data_dir: Optional[Path]) -> List[Path]:
    """Resolve which files feed iter_catalog (precedence order, docstring)."""
    if path is not None:
        p = Path(path)
        if p.is_dir():
            files: List[Path] = []
            for g in _EXPORT_GLOBS:
                files.extend(sorted(p.glob(g)))
            return files
        return [p]

    zone = dropzone_dir(data_dir)
    files = []
    if zone.is_dir():
        for g in _EXPORT_GLOBS:
            files.extend(sorted(zone.glob(g)))
    if files:
        return files

    catalog = _corpus_root(data_dir) / CATALOG_NAME
    return [catalog] if catalog.exists() else []


# ---------------------------------------------------------------------------
# row normalisation — plain dicts in CatalogEntry.to_dict() shape
# ---------------------------------------------------------------------------


def _pick(row: Dict[str, Any], field: str) -> Optional[Any]:
    for alias in _ALIASES[field]:
        v = row.get(alias)
        if v is not None and str(v).strip() != "":
            return v
    return None


def _slug(text: str) -> str:
    out = "".join(c if c.isalnum() else "-" for c in text.lower())
    return "-".join(p for p in out.split("-") if p) or "item"


def _derive_fid(row: Dict[str, Any], title: str, uploader: str) -> str:
    """Stable foreign_identifier without any network access.

    Explicit id wins; a pasted detail-page url contributes its last
    path segment (the site's numeric/slug id); otherwise a crc32 of
    ``title|uploader`` keeps the fid deterministic across re-imports
    (``hash()`` is salted per process — never usable for dedup)."""
    explicit = _pick(row, "fid")
    if explicit is not None:
        return str(explicit).strip()
    url = _pick(row, "url")
    if url:
        tail = str(url).rstrip("/").rsplit("/", 1)[-1].strip()
        if tail:
            return f"lp-{tail}"
    digest = format(zlib.crc32(f"{title}|{uploader}".encode("utf-8")), "08x")
    return f"lp-{_slug(title)}-{digest}"


def _as_bool(v: Any) -> Optional[bool]:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in _TRUE_VALUES


def _entry_from_row(row: Dict[str, Any], *, provenance: str) -> Optional[Dict[str, Any]]:
    """Normalise one export row into a catalog-shape dict (or skip)."""
    title = _pick(row, "title")
    if title is None:
        return None
    title = str(title).strip()
    uploader = (_pick(row, "uploader") or "")
    uploader = str(uploader).strip()
    fid = _derive_fid(row, title, uploader)
    url = _pick(row, "url")

    meta: Dict[str, Any] = {}
    nested = row.get("meta")
    if isinstance(nested, dict):
        for k in _META_KEYS:
            if nested.get(k) is not None:
                meta[k] = nested[k]
    for k in _META_KEYS:
        v = _pick(row, k)
        if v is not None:
            meta[k] = v
    for k in ("bpm", "time_sig", "duration_s"):
        if k in meta:
            try:
                meta[k] = int(float(str(meta[k]).strip()))
            except (TypeError, ValueError):
                pass
    for k in ("autotune", "adult", "has_lyrics"):
        if k in meta:
            meta[k] = _as_bool(meta[k])
    # uploader free text (description/lyrics/…) is REFUSED by whitelist —
    # it is never copied into meta or anywhere else in the row.
    meta["import_provenance"] = provenance

    status = str(row.get("status") or "pending")
    return {
        "source_id": SOURCE_ID,
        "source": SOURCE_ID,
        "foreign_identifier": fid,
        "external_id": fid,
        "title": title,
        "artist": uploader or None,
        "creator": uploader,
        "creator_url": None,
        "url": str(url) if url else "",
        "source_url": str(url) if url else None,
        "license": "proprietary",
        "license_ref": "proprietary",
        "license_url": None,
        "license_tier": "uploader-terms",
        "release_ok": "no",
        "copyright_notice": None,
        "category": "",
        "status": status,
        "drop_reason": None,
        "meta": meta,
        "fetched": status == "fetched",
    }


# ---------------------------------------------------------------------------
# Adapter contract — manual policy: iter_catalog + license_of ONLY
# ---------------------------------------------------------------------------


def iter_catalog(
    limit: Optional[int] = None,
    offset: int = 0,
    *,
    path: Optional[Path] = None,
    data_dir: Optional[Path] = None,
) -> Iterator[Dict[str, Any]]:
    """Emit catalog rows from hand-maintained local export files ONLY.

    Reads ``path`` / the ``_import/`` drop-zone / the existing
    ``_catalog.json`` (precedence order — see module docstring). No file
    found yields nothing. Rows are deduped by ``foreign_identifier``;
    ``limit``/``offset`` slice the merged stream (SPEC §6.3).
    """
    merged: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for f in _export_files(path, data_dir):
        try:
            rows = iter_export_file(f)
        except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
            continue  # unreadable/badly-formed export file — skip, don't die
        for raw in rows:
            entry = _entry_from_row(raw, provenance=f.name)
            if entry is None:
                continue
            fid = entry["foreign_identifier"]
            if fid in merged:
                # refresh mutable metadata on re-import (keep first status)
                old = merged[fid]
                old.update({k: v for k, v in entry.items()
                            if k not in ("status", "fetched")})
            else:
                merged[fid] = entry
                order.append(fid)

    entries = [merged[k] for k in order]
    if offset:
        entries = entries[offset:]
    if limit is not None:
        entries = entries[:limit]
    yield from entries


def license_of(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Looperman policy resolution — constant.

    Tier ``uploader-terms`` / ``release_ok='no'`` is the frozen default;
    a per-item upgrade is only ever a documented per-uploader grant
    recorded as a user decision on the item (``modified_note``), never
    adapter logic (SPEC §1.1)."""
    return {
        "license": "proprietary",
        "license_url": None,
        "license_tier": "uploader-terms",
        "release_ok": "no",
        "copyright_notice": None,
    }


# NOTE: no fetch_lyrics() here — manual sources have no fetch path by
# contract (SPEC §6.3); registry.require_fetchable raises FetchPolicyError
# before this module is ever asked for one. And there is no network code
# in this module at all — enforced by tests/test_lyrics_sources_catalog.py.
