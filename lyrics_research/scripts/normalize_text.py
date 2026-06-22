#!/usr/bin/env python3
"""Normalize Serbian/Bosnian/Croatian/Montenegrin lyrics to Latin script.

Only Cyrillic -> Latin is performed. Latin input is preserved.
Diacritics (š, đ, č, ć, ž) are kept.
"""

from __future__ import annotations

import json
from pathlib import Path

CYRILLIC_TO_LATIN = {
    "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Ђ": "Đ", "Е": "E", "Ж": "Ž",
    "З": "Z", "И": "I", "Ј": "J", "К": "K", "Л": "L", "Љ": "Lj", "М": "M", "Н": "N",
    "Њ": "Nj", "О": "O", "П": "P", "Р": "R", "С": "S", "Т": "T", "Ћ": "Ć", "У": "U",
    "Ф": "F", "Х": "H", "Ц": "C", "Ч": "Č", "Џ": "Dž", "Ш": "Š",
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ђ": "đ", "е": "e", "ж": "ž",
    "з": "z", "и": "i", "ј": "j", "к": "k", "л": "l", "љ": "lj", "м": "m", "н": "n",
    "њ": "nj", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "ћ": "ć", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "č", "џ": "dž", "ш": "š",
}


def to_latin(text: str) -> str:
    """Transliterate Cyrillic characters to Latin script."""
    result = []
    for ch in text:
        if ch in CYRILLIC_TO_LATIN:
            result.append(CYRILLIC_TO_LATIN[ch])
        else:
            result.append(ch)
    return "".join(result)


def normalize_lyrics(text: str) -> str:
    """Return lyrics in Latin script with consistent line breaks."""
    text = text.replace("\r\n", "\n")
    text = to_latin(text)
    return text.strip()


def normalize_dataset(project_root: Path, input_name: str, output_name: str) -> None:
    dataset_path = project_root / "data" / input_name
    output_path = project_root / "data" / output_name

    with dataset_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    for song in data["songs"]:
        song["lyrics_latin"] = normalize_lyrics(song["lyrics"])

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Normalized dataset saved to {output_path}")


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    normalize_dataset(project_root, "dataset_10_songs.json", "dataset_10_songs_normalized.json")
    normalize_dataset(project_root, "dataset_10_songs_rap.json", "dataset_10_songs_rap_normalized.json")


if __name__ == "__main__":
    main()
