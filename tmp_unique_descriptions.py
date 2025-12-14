import json
import re
from pathlib import Path


def main() -> None:
    root = Path(r"C:\Users\cc\Documents\Project\Suno\bulk_downloader_app\suno_library")
    text_path = root / "lyrics_export.txt"
    raw = text_path.read_text(encoding="utf-8")

    entries = []
    current_title = None
    mode = None
    buf = []

    def flush_desc() -> None:
        nonlocal buf
        if not buf:
            return
        text = "\n".join(buf)
        clean = re.sub(r"\[.*?\]", "", text)
        clean = re.sub(r"\s+", " ", clean).strip()
        if clean:
            entries.append((current_title, clean))
        buf = []

    for line in raw.splitlines():
        if line.startswith("# "):
            if mode == "desc":
                flush_desc()
            current_title = line[2:].strip()
            mode = None
            continue
        stripped = line.strip()
        if stripped == "[DESCRIPTION]":
            mode = "desc"
            buf = []
            continue
        if mode == "desc":
            if stripped in {"[LYRICS]", "---"}:
                flush_desc()
                mode = None
                continue
            buf.append(line)

    if mode == "desc":
        flush_desc()

    groups = {}
    for title, desc in entries:
        groups.setdefault(desc, []).append(title)

    unique = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0][:80]))
    data = [{"description": desc, "count": len(titles), "titles": titles} for desc, titles in unique]

    out_path = root / "unique_descriptions.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {len(data)} unique descriptions to {out_path}")
    print("Top 5 groups (count, first title):")
    for desc, titles in unique[:5]:
        print(f"  {len(titles):4d}x - {titles[0]}")


if __name__ == "__main__":
    main()
