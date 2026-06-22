#!/usr/bin/env python3
"""Quantitative analysis of the Serbian/Bosnian lyrics dataset."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


def tokenize(text: str) -> list[str]:
    """Lowercase and extract alphabetic tokens including diacritics."""
    return re.findall(r"[a-zšđčćž]+", text.lower())


def english_words(tokens: list[str]) -> list[str]:
    """Heuristic: tokens that are common English words or brand names."""
    common_english = {
        "the", "and", "for", "you", "are", "not", "but", "with", "your", "from",
        "have", "has", "had", "this", "that", "when", "where", "what", "who",
        "how", "why", "yes", "no", "hey", "ho", "go", "tell", "know", "time",
        "its", "just", "only", "like", "all", "get", "got", "can", "will", "would",
        "show", "some", "everybody", "put", "hands", "up", "we", "ve", "ll", "re",
        "oh", "yeah", "u", "mwah", "kiss", "da", "ba", "he", "she", "they", "them",
        "his", "her", "our", "my", "mine", "its", "it", "is", "am", "be", "been",
        "being", "do", "does", "did", "done", "doing", "so", "if", "because", "as",
        "than", "then", "now", "here", "there", "again", "once", "never", "always",
        "every", "one", "two", "three", "four", "first", "last", "next", "other",
        "new", "old", "good", "bad", "big", "small", "little", "right", "left",
        "love", "live", "alive", "high", "drive", "dry", "forever", "toy", "boy",
        "game", "chess", "single", "multiplayer", "artificial", "intelligence",
        "modern", "technology", "generation", "queen", "king", "boom", "bang",
        # Hip-hop / drill additions
        "bitch", "mode", "switch", "broke", "gangsta", "nasty", "girl", "squad",
        "fashion", "models", "money", "cash", "drill", "trap", "rap", "magic",
        "playback", "vroom", "ave", "choky", "felna", "brena", "hotel", "barca",
        "face", "time", "supreme", "bmw", "benz", "red", "bull", "dior", "gucci",
        "fendi", "vuitton", "louis", "paciotti", "martini", "bikini", "popov",
        "amor", "naomi", "dogg", "tarantino", "wannabe", "taxi", "fashion", "tv",
    }
    return [t for t in tokens if t in common_english]


def analyze_song(song: dict) -> dict:
    lyrics = song["lyrics_latin"] if "lyrics_latin" in song else song["lyrics"]
    lines = [line for line in lyrics.splitlines() if line.strip()]
    tokens = tokenize(lyrics)
    unique_tokens = set(tokens)
    english = english_words(tokens)

    line_lengths = [len(tokenize(line)) for line in lines]
    avg_line_length = sum(line_lengths) / len(line_lengths) if line_lengths else 0

    counter = Counter(tokens)
    top_words = counter.most_common(10)

    repeated_lines = Counter(lines).most_common(5)
    hook_candidates = [(line, count) for line, count in repeated_lines if count > 1]

    return {
        "id": song["id"],
        "artist": song["artist"],
        "title": song["title"],
        "line_count": len(lines),
        "token_count": len(tokens),
        "unique_token_count": len(unique_tokens),
        "type_token_ratio": round(len(unique_tokens) / len(tokens), 3) if tokens else 0,
        "avg_line_length": round(avg_line_length, 2),
        "english_word_ratio": round(len(english) / len(tokens), 3) if tokens else 0,
        "top_words": top_words,
        "hook_lines": hook_candidates,
    }


def build_corpus(data: dict) -> str:
    parts = []
    for song in data["songs"]:
        lyrics = song["lyrics_latin"] if "lyrics_latin" in song else song["lyrics"]
        parts.append(f"# {song['artist']} - {song['title']}\n{lyrics}")
    return "\n\n".join(parts)


def analyze_dataset(project_root: Path, dataset_name: str, analysis_name: str, corpus_name: str) -> None:
    dataset_path = project_root / "data" / dataset_name
    if not dataset_path.exists():
        print(f"Dataset not found: {dataset_path}")
        return

    with dataset_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    analyses = [analyze_song(song) for song in data["songs"]]

    analysis_output = {
        "project": data["project"],
        "collection_date": data.get("collection_date", ""),
        "song_count": len(analyses),
        "aggregate": {
            "total_lines": sum(a["line_count"] for a in analyses),
            "total_tokens": sum(a["token_count"] for a in analyses),
            "avg_type_token_ratio": round(
                sum(a["type_token_ratio"] for a in analyses) / len(analyses), 3
            ),
            "avg_english_ratio": round(
                sum(a["english_word_ratio"] for a in analyses) / len(analyses), 3
            ),
        },
        "songs": analyses,
    }

    analysis_path = project_root / "data" / analysis_name
    with analysis_path.open("w", encoding="utf-8") as f:
        json.dump(analysis_output, f, ensure_ascii=False, indent=2)
    print(f"Analysis saved to {analysis_path}")

    corpus = build_corpus(data)
    corpus_path = project_root / "data" / corpus_name
    with corpus_path.open("w", encoding="utf-8") as f:
        f.write(corpus)
    print(f"Corpus saved to {corpus_path}")


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    analyze_dataset(
        project_root,
        "dataset_10_songs_normalized.json",
        "analysis.json",
        "corpus.txt",
    )
    analyze_dataset(
        project_root,
        "dataset_10_songs_rap_normalized.json",
        "analysis_rap.json",
        "corpus_rap.txt",
    )


if __name__ == "__main__":
    main()
