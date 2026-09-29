"""Per-corpus catalog writer — ``<corpus>/_catalog.json`` (SPEC §3.1).

The catalog IS the resumable work queue / status file (AGENTS.md batch
pattern): every ``CatalogEntry`` row carries ``status``
(``pending|fetched|skipped|failed|dropped``), ``drop_reason``, license fields,
and catalog metadata; the file is flushed after every item mutation so an
interrupted run resumes exactly where it stopped.

Used by ALL adapters, including catalog-only ones (pdinfo emits entries with
``status='pending'`` that never get fetched — there is no fetch path for
``fetch_policy != 'auto'``).

NOTE on filename: the W1 task text said ``_catalog.jsonl``; the frozen SPEC
(§3.1, §6.2, §6.4 — the authoritative doc) names it ``_catalog.json``, a
single flushed JSON document. Implemented as ``_catalog.json``.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    from ._common import (
        CATALOG_VERSION,
        CatalogEntry,
        entry_from_dict,
        load_catalog,
        pending_slice,
        save_catalog,
    )
except ImportError:  # sources/ dir directly on sys.path
    from _common import (  # type: ignore
        CATALOG_VERSION,
        CatalogEntry,
        entry_from_dict,
        load_catalog,
        pending_slice,
        save_catalog,
    )

CATALOG_FILENAME = "_catalog.json"


class Catalog:
    """Resumable ``_catalog.json`` work queue for one corpus.

    Semantics mirror ``toolshop/batch.py`` (self-contained — no toolshop
    import): status per item, flushed on every mutation; ``resume=True``
    skips terminal statuses (``fetched``/``skipped``/``dropped``) and retries
    ``failed``.
    """

    def __init__(self, path: Path, doc: Optional[Dict[str, Any]] = None) -> None:
        self.path = Path(path)
        self.doc = doc if doc is not None else load_catalog(self.path)
        self.doc.setdefault("entries", [])
        # fast lookup: entry key -> index into doc["entries"]
        self._by_key: Dict[str, int] = {}
        for i, e in enumerate(self.doc["entries"]):
            self._by_key[self._entry_key(e)] = i

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------

    @classmethod
    def load_or_create(
        cls,
        path: Path,
        *,
        source_id: Optional[str] = None,
        corpus: Optional[str] = None,
    ) -> "Catalog":
        cat = cls(path)
        if not cat.doc.get("created"):
            cat.doc["created"] = datetime.now().isoformat()
        if source_id and not cat.doc.get("source"):
            cat.doc["source"] = source_id
        if corpus and not cat.doc.get("corpus"):
            cat.doc["corpus"] = corpus
        cat.doc.setdefault("version", CATALOG_VERSION)
        return cat

    @classmethod
    def for_corpus(
        cls,
        corpus_root: Path,
        *,
        source_id: Optional[str] = None,
        corpus: Optional[str] = None,
    ) -> "Catalog":
        return cls.load_or_create(
            Path(corpus_root) / CATALOG_FILENAME,
            source_id=source_id,
            corpus=corpus,
        )

    # ------------------------------------------------------------------
    # entries
    # ------------------------------------------------------------------

    @staticmethod
    def _entry_key(e: Dict[str, Any]) -> str:
        fid = e.get("foreign_identifier") or e.get("external_id")
        if fid:
            return f"fid:{fid}"
        try:
            return entry_from_dict(e).key()
        except Exception:
            return f"tu:{e.get('title','')}:{e.get('url','')}"

    @property
    def entries(self) -> List[Dict[str, Any]]:
        return self.doc["entries"]

    def find(self, foreign_identifier: str) -> Optional[Dict[str, Any]]:
        idx = self._by_key.get(f"fid:{foreign_identifier}")
        return self.entries[idx] if idx is not None else None

    def upsert_entries(
        self, entries: Iterable[Any], *, flush: bool = True
    ) -> int:
        """Merge adapter-emitted entries into the queue.

        New entries are appended (``status='pending'`` unless the adapter set
        one); existing keys keep their stored status — re-listing a catalog
        never resurrects terminal items. Returns the number of NEW entries.
        """
        added = 0
        for item in entries:
            d = item.to_dict() if isinstance(item, CatalogEntry) else dict(item)
            d.setdefault("status", "pending")
            key = self._entry_key(d)
            if key in self._by_key:
                idx = self._by_key[key]
                old = self.entries[idx]
                # refresh mutable metadata but preserve status/drop_reason
                keep = {k: old[k] for k in ("status", "drop_reason", "error",
                                            "json_path") if k in old}
                old.update(d)
                old.update(keep)
            else:
                self._by_key[key] = len(self.entries)
                self.entries.append(d)
                added += 1
        if flush:
            self.save()
        return added

    def mark(
        self,
        foreign_identifier: str,
        status: str,
        *,
        drop_reason: Optional[str] = None,
        error: Optional[str] = None,
        json_path: Optional[str] = None,
        flush: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Set an entry's status by upstream id + flush."""
        e = self.find(foreign_identifier)
        if e is None:
            return None
        return self.mark_entry(
            e, status, drop_reason=drop_reason, error=error,
            json_path=json_path, flush=flush,
        )

    def mark_entry(
        self,
        e: Dict[str, Any],
        status: str,
        *,
        drop_reason: Optional[str] = None,
        error: Optional[str] = None,
        json_path: Optional[str] = None,
        flush: bool = True,
    ) -> Dict[str, Any]:
        """Set a status on a stored entry dict (identity-based — works even
        for entries with no ``foreign_identifier``) and flush."""
        e["status"] = status
        e["fetched"] = status == "fetched"
        if drop_reason is not None:
            e["drop_reason"] = drop_reason
        if error is not None:
            e["error"] = error
        elif status != "failed":
            e.pop("error", None)
        if json_path is not None:
            e["json_path"] = json_path
        if flush:
            self.save()
        return e

    def pending(
        self,
        *,
        resume: bool = True,
        category: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        return pending_slice(
            self.entries, resume=resume, category=category,
            limit=limit, offset=offset,
        )

    def counts(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for e in self.entries:
            st = e.get("status") or "pending"
            out[st] = out.get(st, 0) + 1
        return out

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    @staticmethod
    def _refresh_aliases(e: Dict[str, Any]) -> None:
        """Keep the task-named alias fields consistent with the canonical
        SPEC §6.2 fields before the doc hits disk."""
        e["fetched"] = (e.get("status") == "fetched")
        if e.get("source") is None and e.get("source_id"):
            e["source"] = e["source_id"]
        e["external_id"] = e.get("foreign_identifier") or e.get("external_id")
        e["license_ref"] = e.get("license") or e.get("license_ref")
        if e.get("artist") is None and e.get("creator"):
            e["artist"] = e["creator"]

    def save(self) -> None:
        for e in self.doc["entries"]:
            self._refresh_aliases(e)
        save_catalog(self.doc, self.path)


def write_catalog(
    path: Path,
    entries: Iterable[Any],
    *,
    source_id: Optional[str] = None,
    corpus: Optional[str] = None,
) -> Catalog:
    """One-shot: build/merge a catalog file from adapter entries and flush.
    Returns the Catalog for further marking."""
    cat = Catalog.load_or_create(path, source_id=source_id, corpus=corpus)
    cat.upsert_entries(entries, flush=False)
    cat.save()
    return cat
