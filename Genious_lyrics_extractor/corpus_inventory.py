"""Full corpus inventory for handoff."""
import sqlite3
from pathlib import Path

db_path = Path(r"D:\MusicData\toolshop\lyrics\lyrics.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Total songs
total = cur.execute("SELECT COUNT(*) FROM songs WHERE corpus='genius-pro'").fetchone()[0]
print(f"=== CORPUS INVENTORY ===\n")
print(f"Total songs: {total}")

# Per-artist solo counts with cohort
rows = cur.execute("""
    SELECT target_artist, genre_cohort, COUNT(*) as cnt
    FROM songs WHERE corpus='genius-pro' AND role='solo'
    GROUP BY target_artist, genre_cohort
    ORDER BY genre_cohort, cnt DESC
""").fetchall()

print(f"\n--- Solo songs by artist ({sum(r[2] for r in rows)} total) ---")
current_cohort = None
for artist, cohort, count in rows:
    if cohort != current_cohort:
        current_cohort = cohort
        print(f"\n  [{cohort or 'NULL'}]")
    print(f"    {artist:25s}: {count}")

# Featured songs
feat = cur.execute("""
    SELECT target_artist, genre_cohort, COUNT(*)
    FROM songs WHERE corpus='genius-pro' AND role='featured'
    GROUP BY target_artist, genre_cohort
    ORDER BY genre_cohort, COUNT(*) DESC
""").fetchall()
print(f"\n--- Featured songs ({sum(r[2] for r in feat)} total) ---")
for artist, cohort, count in feat:
    print(f"  {artist:25s} [{cohort or 'NULL':10s}]: {count}")

# Sections, lines, rhymes
sections = cur.execute("SELECT COUNT(*) FROM sections").fetchone()[0]
lines = cur.execute("SELECT COUNT(*) FROM lines").fetchone()[0]
rhymes = cur.execute("SELECT COUNT(*) FROM line_rhymes").fetchone()[0]
song_metrics = cur.execute("SELECT COUNT(*) FROM song_rhyme_metrics").fetchone()[0]
print(f"\n--- Structural counts ---")
print(f"  Sections: {sections}")
print(f"  Lines: {lines}")
print(f"  Rhyme rows: {rhymes}")
print(f"  Song rhyme metrics: {song_metrics}")

# Batch breakdown by folder
print(f"\n--- Files on disk by category ---")
rows = cur.execute("""
    SELECT category, COUNT(*) FROM songs WHERE corpus='genius-pro'
    GROUP BY category ORDER BY category
""").fetchall()
for cat, count in rows:
    print(f"  {cat:30s}: {count}")

# NULL cohort investigation
null_solo = cur.execute("""
    SELECT target_artist, COUNT(*) FROM songs 
    WHERE corpus='genius-pro' AND role='solo' AND genre_cohort IS NULL
    GROUP BY target_artist ORDER BY COUNT(*) DESC
""").fetchall()
print(f"\n--- NULL cohort solo artists (need COHORT_MAP entry) ---")
for artist, count in null_solo:
    print(f"  {artist:25s}: {count}")

conn.close()
