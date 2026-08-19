#!/usr/bin/env python3
"""Fetch the Suno catalogue from the CDN to local disk (preservation pass).

Context
-------
`data/toolshop/suno/*_metadata.json` holds 3,426 records whose ``audio_url`` points at
``https://cdn1.suno.ai/<id>.mp3``. Those tracks exist on this machine *only* as links.
No backup can protect a file that was never downloaded, so this script fetches them.

Plan: ``docs/superpowers/plans/2026-08-19-suno-catalogue-preservation.md``
Prior art: ``D:\\Projects\\suno_extractor\\suno_downloader.py`` (same CDN hosts, same
retry shape; that one consumes a different metadata schema, so this is a focused
re-implementation against the toolshop records rather than a bent import).

Behaviour
---------
- **Resume by default.** A file already on disk whose size matches the manifest (or the
  CDN ``Content-Length``) is skipped. Partial or mismatched files are re-fetched.
- **Integrity per file.** Bytes written are compared against ``Content-Length``; a
  mismatch discards the file and retries. ``sha256`` is recorded for every keeper.
- **Polite.** 4 workers, capped retries, exponential backoff on 429/5xx. Sustained 429s
  abort the run rather than escalating.
- **A dead link is data, not a crash.** Failures are recorded and the run continues.

Usage
-----
    python scripts/suno_fetch_catalogue.py --dry-run
    python scripts/suno_fetch_catalogue.py --limit 20
    python scripts/suno_fetch_catalogue.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
SUNO_DIR = REPO_ROOT / "data" / "toolshop" / "suno"
AUDIO_DIR = SUNO_DIR / "audio"
MANIFEST_PATH = AUDIO_DIR / "_download_manifest.json"

MAX_WORKERS = 4
MAX_ATTEMPTS = 3
REQUEST_TIMEOUT = 60
CHUNK = 1 << 16
USER_AGENT = "Mozilla/5.0 (toolshop suno preservation pass)"

# Sustained rate limiting means stop, not push harder.
RATE_LIMIT_ABORT_THRESHOLD = 25

_manifest_lock = threading.Lock()
_rate_limit_hits = threading.Event()
_rate_limit_count = 0


# --------------------------------------------------------------------------- records


def load_records(limit: Optional[int] = None) -> List[Dict]:
    """Read the Suno metadata files into fetch records."""
    files = sorted(SUNO_DIR.glob("*_metadata.json"))
    records: List[Dict] = []
    reconstructed: List[str] = []
    skipped = 0
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            skipped += 1
            continue
        song_id = (data.get("id") or "").strip()
        url = (data.get("audio_url") or "").strip()
        if not song_id:
            skipped += 1
            continue
        if not url:
            # 17 records carry a title but no audio_url. The CDN path is deterministic
            # (verified 2026-08-19: constructed URLs returned 200 with real byte counts),
            # so reconstruct rather than write the track off.
            url = f"https://cdn1.suno.ai/{song_id}.mp3"
            reconstructed.append(song_id)
        records.append(
            {
                "id": song_id,
                "url": url,
                "url_reconstructed": song_id in reconstructed,
                "title": data.get("title") or "",
                "artist": data.get("display_name") or data.get("handle") or "",
                "created_at": data.get("created_at") or "",
                "model": data.get("model_name") or "",
            }
        )
    if skipped:
        print(f"[warn] {skipped} metadata file(s) unreadable or missing an id")
    if reconstructed:
        print(f"[info] {len(reconstructed)} record(s) had no audio_url; CDN path reconstructed from id")

    # Distinct ids only - the same track can appear in more than one export.
    seen = set()
    unique = []
    for r in records:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        unique.append(r)
    if len(unique) != len(records):
        print(f"[info] collapsed {len(records) - len(unique)} duplicate id(s)")

    return unique[:limit] if limit else unique


def load_manifest() -> Dict[str, Dict]:
    if not MANIFEST_PATH.exists():
        return {}
    try:
        raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        return {e["id"]: e for e in raw.get("entries", []) if e.get("id")}
    except Exception as exc:  # a corrupt manifest must not block a re-fetch
        print(f"[warn] manifest unreadable ({exc}); starting a fresh one")
        return {}


def write_manifest(entries: Dict[str, Dict]) -> None:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "audio_dir": str(AUDIO_DIR),
        "count": len(entries),
        "entries": sorted(entries.values(), key=lambda e: e.get("id", "")),
    }
    tmp = MANIFEST_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(MANIFEST_PATH)


# --------------------------------------------------------------------------- fetching


def _sleep_backoff(attempt: int) -> None:
    time.sleep(min(30.0, (2 ** attempt) + random.uniform(0, 0.75)))


def fetch_one(rec: Dict, prior: Optional[Dict], session: requests.Session) -> Dict:
    """Download one track. Returns a manifest entry."""
    global _rate_limit_count

    song_id = rec["id"]
    dest = AUDIO_DIR / f"{song_id}.mp3"
    base = {
        "id": song_id,
        "url": rec["url"],
        "title": rec["title"],
        "artist": rec["artist"],
        "created_at": rec["created_at"],
        "model": rec["model"],
    }

    # Resume: trust a prior manifest entry whose file is still the right size on disk.
    if prior and prior.get("status") == "ok" and dest.exists():
        expected = prior.get("bytes")
        if expected and dest.stat().st_size == expected:
            out = dict(prior)
            out["status"] = "skipped"
            return out

    for attempt in range(MAX_ATTEMPTS):
        if _rate_limit_hits.is_set():
            return {**base, "status": "aborted", "reason": "rate_limited", "attempts": attempt}
        try:
            with session.get(
                rec["url"],
                stream=True,
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
            ) as resp:
                if resp.status_code == 429 or resp.status_code >= 500:
                    with _manifest_lock:
                        _rate_limit_count += 1
                        if _rate_limit_count >= RATE_LIMIT_ABORT_THRESHOLD:
                            _rate_limit_hits.set()
                    _sleep_backoff(attempt)
                    continue
                if resp.status_code != 200:
                    return {
                        **base,
                        "status": "failed",
                        "http_status": resp.status_code,
                        "attempts": attempt + 1,
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                    }

                declared = resp.headers.get("Content-Length")
                declared_n = int(declared) if declared and declared.isdigit() else None

                # Already on disk at the right size, with no manifest entry to trust.
                if dest.exists() and declared_n and dest.stat().st_size == declared_n:
                    return {
                        **base,
                        "status": "skipped",
                        "bytes": declared_n,
                        "sha256": prior.get("sha256") if prior else None,
                        "http_status": 200,
                        "attempts": attempt + 1,
                    }

                tmp = dest.with_suffix(".mp3.part")
                digest = hashlib.sha256()
                written = 0
                with open(tmp, "wb") as fh:
                    for chunk in resp.iter_content(CHUNK):
                        if not chunk:
                            continue
                        fh.write(chunk)
                        digest.update(chunk)
                        written += len(chunk)

                if declared_n is not None and written != declared_n:
                    tmp.unlink(missing_ok=True)
                    _sleep_backoff(attempt)
                    continue
                if written == 0:
                    tmp.unlink(missing_ok=True)
                    _sleep_backoff(attempt)
                    continue

                tmp.replace(dest)
                return {
                    **base,
                    "status": "ok",
                    "bytes": written,
                    "sha256": digest.hexdigest(),
                    "http_status": 200,
                    "attempts": attempt + 1,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }

        except Exception as exc:
            if attempt == MAX_ATTEMPTS - 1:
                return {
                    **base,
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                    "attempts": attempt + 1,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
            _sleep_backoff(attempt)

    return {
        **base,
        "status": "failed",
        "error": "exhausted retries",
        "attempts": MAX_ATTEMPTS,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


# --------------------------------------------------------------------------- main


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Fetch the Suno catalogue to local disk.")
    ap.add_argument("--limit", type=int, default=None, help="only process the first N records")
    ap.add_argument("--dry-run", action="store_true", help="report what would happen, fetch nothing")
    ap.add_argument("--workers", type=int, default=MAX_WORKERS, help=f"parallel downloads (default {MAX_WORKERS})")
    args = ap.parse_args(argv)

    if not SUNO_DIR.exists():
        print(f"[error] no Suno metadata directory at {SUNO_DIR}")
        return 2

    records = load_records(args.limit)
    manifest = load_manifest()
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    on_disk = {p.stem for p in AUDIO_DIR.glob("*.mp3")}
    todo = [r for r in records if not (r["id"] in on_disk and manifest.get(r["id"], {}).get("status") == "ok")]

    print(f"records:        {len(records)}")
    print(f"already on disk:{len(on_disk):>6}")
    print(f"to fetch:       {len(todo):>6}")
    print(f"est. size:      ~{len(todo) * 3.9 / 1024:.2f} GB at ~3.9 MB/track")
    print(f"destination:    {AUDIO_DIR}")

    if args.dry_run:
        print("\n[dry-run] nothing fetched")
        for r in todo[:5]:
            print(f"  would fetch {r['id']}  {r['title'][:60]}")
        return 0

    if not todo:
        print("\nnothing to do - catalogue is complete")
        return 0

    started = time.time()
    done = ok = skipped = failed = 0
    total_bytes = 0

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(fetch_one, r, manifest.get(r["id"]), session): r for r in todo
        }
        for fut in as_completed(futures):
            entry = fut.result()
            done += 1
            status = entry.get("status")
            if status == "ok":
                ok += 1
                total_bytes += entry.get("bytes") or 0
            elif status == "skipped":
                skipped += 1
            else:
                failed += 1

            with _manifest_lock:
                manifest[entry["id"]] = entry
                if done % 50 == 0 or done == len(todo):
                    write_manifest(manifest)

            if done % 25 == 0 or done == len(todo):
                rate = done / max(1e-9, time.time() - started)
                remaining = (len(todo) - done) / rate if rate else 0
                print(
                    f"  {done}/{len(todo)}  ok={ok} skip={skipped} fail={failed}  "
                    f"{total_bytes/2**30:.2f} GB  ~{remaining/60:.0f} min left",
                    flush=True,
                )

            if _rate_limit_hits.is_set():
                print("\n[abort] sustained rate limiting from the CDN - stopping.")
                print("        Re-run later; resume will pick up exactly what is missing.")
                break

    with _manifest_lock:
        write_manifest(manifest)

    elapsed = time.time() - started
    print("\n" + "=" * 60)
    print(f"fetched:  {ok}")
    print(f"skipped:  {skipped}")
    print(f"failed:   {failed}")
    print(f"bytes:    {total_bytes/2**30:.2f} GB")
    print(f"elapsed:  {elapsed/60:.1f} min")
    print(f"manifest: {MANIFEST_PATH}")

    if failed:
        print("\nfailures:")
        for e in manifest.values():
            if e.get("status") in ("failed", "aborted"):
                why = e.get("error") or e.get("http_status") or e.get("reason")
                print(f"  {e['id']}  {why}  {e.get('title','')[:50]}")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
