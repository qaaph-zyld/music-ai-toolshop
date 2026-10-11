# PLAN — audition_review v2 (lane/audition-review-v2)

Scope = PROMPT.md checklist. Worktree: `D:\Projects\Music-AI-Toolshop-wt-audition-v2`. Test port: **8781**. Never touch master's tree, wt-audition, toolshop/hub, ORCHESTRATION/hub, or the :8778 server.

- [ ] 0. Worktree + import probe (`m.__file__` → wt-audition-v2) + sha256 snapshot of the mojgrad JSONL
- [ ] 1. RED: extend `tests/test_audition_review.py` (config ordering/states, no-config unchanged, round flip + reused-prefix refusal, /songs, check exit codes, WIDGET_JS `audition:saved`, JSONL schema)
- [ ] 2. `scripts/audition_review.py`: `audition.json` loader, group-ordered decorated `page` (STYLE/LEGEND/TODO/`g-*`/`data-tag` from build_page.py), WIDGET_JS dispatches `audition:saved`, `GET /__audition__/songs`, `round`, `check`, overwrite guard
- [ ] 3. Migrate mojgrad pack: write `audition.json`, regen `index.html`, serve 8781
- [ ] 4. Overwrite workflow canonical + 2 mirrors (byte-identical), `gen_index.py`
- [ ] 5. Acceptance A1–A7 (pytest >32, DOM 2/14/4/5, check 206s, songs list, JSONL hash, wf hashes, kill 8781)
- [ ] 6. Commit lane + ai_dev_meta_layer (explicit pathspecs), handoff in `.workspace_archive/handoffs/`, STOP — no merge
