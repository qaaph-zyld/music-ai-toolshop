import json
from pathlib import Path

status_path = Path(r"d:\Projects\Music-AI-Toolshop\results\crhymetv_re\batch_status.json")
d = json.loads(status_path.read_text(encoding="utf-8"))
print(f"Total: {d['total_tracks']}")
print(f"Last completed index: {d['last_completed_index']}")
print(f"Finished: {d.get('finished')}")
print(f"Tracks in status: {len(d['tracks'])}")
completed = [t for t in d['tracks'] if t['status'] == 'completed']
failed = [t for t in d['tracks'] if t['status'] == 'failed']
print(f"Completed: {len(completed)}")
print(f"Failed: {len(failed)}")
print(f"Errors: {len(d.get('errors', []))}")
for t in failed[:10]:
    err = (t.get('error') or '')[:120]
    print(f"  FAIL: {t['slug']}: {err}")
for e in d.get('errors', [])[:5]:
    print(f"  ERR: {e[:120]}")
