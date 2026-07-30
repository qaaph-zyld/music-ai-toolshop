"""Verify batch 3 cohort counts in lyrics.db."""
import sqlite3
from pathlib import Path
from collections import Counter

db_path = Path(__file__).resolve().parent.parent / "data" / "toolshop" / "lyrics" / "lyrics.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Total songs
total = cur.execute("SELECT COUNT(*) FROM songs WHERE corpus='genius-pro'").fetchone()[0]
print(f"Total songs: {total}")

# By cohort
rows = cur.execute("""
    SELECT genre_cohort, role, COUNT(*) 
    FROM songs WHERE corpus='genius-pro'
    GROUP BY genre_cohort, role
    ORDER BY genre_cohort, role
""").fetchall()
print("\nCohort breakdown:")
for cohort, role, count in rows:
    print(f"  {cohort or 'NULL':15s} {role:10s}: {count}")

# By target_artist (solo only)
rows = cur.execute("""
    SELECT target_artist, genre_cohort, COUNT(*)
    FROM songs WHERE corpus='genius-pro' AND role='solo'
    GROUP BY target_artist, genre_cohort
    ORDER BY genre_cohort, target_artist
""").fetchall()
print("\nSolo songs by artist:")
for artist, cohort, count in rows:
    print(f"  {artist:20s} [{cohort or 'NULL':10s}]: {count}")

# Sections and lines
sections = cur.execute("SELECT COUNT(*) FROM sections").fetchone()[0]
lines = cur.execute("SELECT COUNT(*) FROM lines").fetchone()[0]
rhymes = cur.execute("SELECT COUNT(*) FROM line_rhymes").fetchone()[0]
print(f"\nSections: {sections}")
print(f"Lines: {lines}")
print(f"Rhyme rows: {rhymes}")

conn.close()
