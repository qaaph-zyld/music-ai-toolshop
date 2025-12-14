import re
import json
import math
from pathlib import Path
from collections import Counter, defaultdict

root = Path(r"C:\Users\cc\Documents\Project\Suno\bulk_downloader_app\suno_library")
text_path = root / "lyrics_export.txt"
raw = text_path.read_text(encoding="utf-8")

blocks = []
current = None
for line in raw.splitlines():
    if line.startswith("# "):
        if current:
            blocks.append(current)
        current = {"title": line[2:].strip(), "lyrics_lines": [], "mode": None}
        continue
    if current is None:
        continue
    if line.strip() == "---":
        current["mode"] = None
        continue
    if line.strip() == "[LYRICS]":
        current["mode"] = "lyrics"
        continue
    if line.startswith("[") and line.endswith("]") and current.get("mode") != "lyrics":
        continue
    if current.get("mode") == "lyrics":
        cleaned = re.sub(r"\[.*?\]", "", line).strip()
        if cleaned:
            current["lyrics_lines"].append(cleaned)

if current:
    blocks.append(current)

songs = []
for b in blocks:
    if b["lyrics_lines"]:
        lyrics = " ".join(b["lyrics_lines"])
        lyrics = re.sub(r"\s+", " ", lyrics).strip()
        if lyrics:
            songs.append({"title": b["title"], "lyrics": lyrics})

if not songs:
    print(json.dumps({"error": "No lyrics found"}, ensure_ascii=False, indent=2))
    raise SystemExit

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans

    corpus = [s["lyrics"] for s in songs]
    vect = TfidfVectorizer(stop_words="english", max_features=5000)
    X = vect.fit_transform(corpus)
    n_clusters = min(6, max(2, int(math.sqrt(len(songs)))))
    km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    labels = km.fit_predict(X)
    terms = vect.get_feature_names_out()
    order_centroids = km.cluster_centers_.argsort()[:, ::-1]
    top_terms = [[terms[ind] for ind in order_centroids[i, :6]] for i in range(n_clusters)]
    clustered = {i: {"terms": top_terms[i], "songs": []} for i in range(n_clusters)}
    for song, label in zip(songs, labels):
        clustered[label]["songs"].append(song)
except Exception:
    def top_token(text: str):
        toks = re.findall(r"[a-zA-ZčćžšđČĆŽŠĐ']+", text.lower())
        c = Counter(toks)
        return tuple([t for t, _ in c.most_common(3)])

    grouped = defaultdict(list)
    for song in songs:
        grouped[top_token(song["lyrics"])].append(song)
    clustered = {i: {"terms": list(k), "songs": v} for i, (k, v) in enumerate(grouped.items())}

summary = []
for cid, data in clustered.items():
    songs_list = data["songs"]
    snippet = songs_list[0]["lyrics"][:240]
    summary.append(
        {
            "cluster": cid,
            "top_terms": data["terms"],
            "count": len(songs_list),
            "examples": [s["title"] for s in songs_list[:5]],
            "snippet": snippet,
        }
    )

print(json.dumps({"clusters": summary}, ensure_ascii=False, indent=2))
