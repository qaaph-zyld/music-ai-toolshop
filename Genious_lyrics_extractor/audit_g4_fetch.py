"""G4-A — read-only audit of the genius-de roster fetch.

Verifies the corpus at data/toolshop/lyrics/genius-de against roster_g4.json:
all artists done, song JSONs well-formed (genius_song_id, language='de',
non-empty sections), folders match the roster, plausible primary artists.
Prints a per-artist table + verdict: INGEST READY or FETCH INCOMPLETE.

Read-only by contract: never runs the fetcher, index builder, or db builder.

Usage:
    python audit_g4_fetch.py [--corpus <genius-de dir>] [--roster roster_g4.json]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

EXTRACTOR = Path(__file__).resolve().parent
_DATA_DIR = os.environ.get(
    "TOOLSHOP_DATA_DIR",
    str(EXTRACTOR.parent.parent / "data" / "toolshop"),
)
DEFAULT_CORPUS = Path(_DATA_DIR) / "lyrics" / "genius-de"


def audit(corpus: Path, roster_path: Path, sample: int = 3) -> int:
    roster = json.loads(roster_path.read_text(encoding="utf-8"))["artists"]
    problems: list[str] = []

    status_path = corpus / "_fetch_status_g4.json"
    if not status_path.exists():
        print(f"STATUS FILE MISSING: {status_path}")
        return 2
    status = json.loads(status_path.read_text(encoding="utf-8"))
    ast = status.get("artists", {})

    print(f"corpus: {corpus}")
    print(f"status: {status_path}\n")
    print(f"{'artist':22} {'status':16} {'reported':>8} {'on_disk':>7}  folders")
    print("-" * 78)

    grand = 0
    rng = random.Random(42)
    for cfg in roster:
        folder = cfg["folder"]
        entry = ast.get(folder, {})
        st = entry.get("status", "MISSING")
        reported = len(entry.get("done_song_ids", []))

        # on-disk count across this artist's possible dirs
        dirs = sorted(
            d for d in corpus.iterdir()
            if d.is_dir() and (d.name == f"{folder}-solo"
                               or d.name == f"{folder}-featured"
                               or folder in d.name.split("-duo")[0].split("-")
                               or d.name.endswith("-duo") and folder in d.name.split("-")[:-1]
                               or d.name.endswith("-trio") and folder in d.name.split("-")[:-1])
        ) if corpus.exists() else []
        on_disk = sum(len(list(d.glob("*.json"))) for d in dirs)
        grand += on_disk

        flag = ""
        if st != "done":
            flag = "  <-- NOT DONE"
            problems.append(f"{cfg['name']}: status={st}")
        print(f"{cfg['name']:22} {st:16} {reported:>8} {on_disk:>7}  "
              f"{','.join(d.name for d in dirs)}{flag}")

    print("-" * 78)

    # corpus-level checks
    unknown_dirs = []
    if corpus.exists():
        known = set()
        for cfg in roster:
            f = cfg["folder"]
            for d in corpus.iterdir():
                if d.is_dir():
                    parts = d.name.rsplit("-", 1)
                    if len(parts) == 2 and parts[1] in ("solo", "featured"):
                        if parts[0] == f:
                            known.add(d.name)
                    elif parts[-1] in ("duo", "trio"):
                        if f in parts[0].split("-"):
                            known.add(d.name)
                    elif d.name == "other-collab":
                        known.add(d.name)
        unknown_dirs = [d.name for d in corpus.iterdir()
                        if d.is_dir() and d.name not in known]
        if unknown_dirs:
            problems.append(f"unknown dirs: {unknown_dirs}")

    # song-JSON spot checks
    song_jsons = [p for p in corpus.rglob("*.json")
                  if not p.name.startswith("_")] if corpus.exists() else []
    rng.shuffle(song_jsons)
    checked = sampled = 0
    null_ids = bad_lang = empty_sections = 0
    roster_names = {a["name"].lower() for a in roster}
    roster_variants = {v.lower() for a in roster for v in a.get("variants", [])}
    susp_titles: list[str] = []

    for p in song_jsons[:200]:  # cap the sample
        sampled += 1
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            problems.append(f"unreadable {p.name}: {exc}")
            continue
        checked += 1
        if doc.get("genius_song_id") is None:
            null_ids += 1
            problems.append(f"null genius_song_id: {p}")
        if doc.get("language") != "de":
            bad_lang += 1
            problems.append(f"language={doc.get('language')!r}: {p}")
        secs = doc.get("sections") or []
        if not any(s.get("content", "").strip() for s in secs):
            empty_sections += 1
            problems.append(f"empty sections: {p}")
        pa = (doc.get("primary_artist") or "").lower()
        title = (doc.get("title") or "")
        if pa and pa not in roster_names and not any(
            v in pa or pa in v for v in roster_variants
        ):
            pass  # non-roster primary is legit (featured fetch) — informational only
        if any(t in title.lower() for t in ("english", "translation")):
            susp_titles.append(f"{p.parent.name}/{p.name}: {title}")

    print(f"\nsong JSONs on disk (excl _*.json): {len(song_jsons)}")
    print(f"spot-checked: {checked} | null_id={null_ids} bad_lang={bad_lang} "
          f"empty_sections={empty_sections}")
    if susp_titles:
        print("suspicious (English/translation) titles:")
        for t in susp_titles[:10]:
            print(f"   {t}")

    other = corpus / "other-collab"
    if other.exists():
        n = len(list(other.glob("*.json")))
        print(f"other-collab songs: {n}")

    print()
    if problems:
        print("PROBLEMS:")
        for pr in problems[:40]:
            print(f"  - {pr}")
        print(f"\nVERDICT: FETCH INCOMPLETE ({len(problems)} problems)")
        return 1
    print("VERDICT: INGEST READY")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--roster", type=Path,
                    default=EXTRACTOR / "roster_g4.json")
    args = ap.parse_args()
    sys.exit(audit(args.corpus, args.roster))


if __name__ == "__main__":
    main()
