# 06 — Expected outcomes (`/define_output`)

**How to read this:**
- Each outcome id is listed with its wave in `05_WAVES.md`.
- Outcomes marked **[live]** need the server running: `python -m toolshop.hub serve`, at
  `HUB_URL=http://127.0.0.1:8790`.
- Every check exits 0 on pass.
- `/check_output` runs the JSON block below unchanged (framework `expected_output_schema`, spec 0.1.0).

**Paths during the build:**
- **Commands:** the commands below use the merged location `D:\Projects\Music-AI-Toolshop`. While building in
  the worktree, run the same commands with the worktree path substituted and `PYTHONPATH` set to the worktree
  (see `05` W0).
- **The checker:** use the copy next to the code under test (the worktree's
  `ORCHESTRATION\hub\checks\contract_checks.py` while building). It reads code-side files such as `hub.css` from
  its own repo, sets `PYTHONPATH` to that repo for the subprocesses it starts, and always reads the indexed data
  from the main checkout `D:\Projects\Music-AI-Toolshop`.

**When a check is wrong:** the builder records the problem in `LEDGER.md` and stops. The builder may not edit the
check; only the orchestrator changes a check, through the `07` change log.

| Wave | Outcomes |
|---|---|
| W0 | O0.1–O0.6 |
| W1 | O1.1–O1.6 |
| W2 | O2.1–O2.8 (+ browser verification + USER GATE) |
| W3 | O3.1–O3.4 |
| W4 | O4.1–O4.5 |
| W5 | O5.1–O5.5 |

```json
{
  "task": "Music Hub v1: local web app (Inbox + Journal with receipts, Lanes & repo health, Artist pages)",
  "slug": "music_hub_v1",
  "stamp": "2026-10-06T00:00:00Z",
  "outcomes": [
    {
      "id": "O0.1",
      "description": "selfcheck passes every runtime-contract item (01_DESIGN)",
      "check_command": "cd /d D:\\Projects\\Music-AI-Toolshop && \"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" -m toolshop.hub selfcheck",
      "check_timeout": 60,
      "constraint_text": ""
    },
    {
      "id": "O0.2",
      "description": "[live] /api/health answers 200 with collectors + indexed_at",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" health",
      "check_timeout": 60,
      "constraint_text": ""
    },
    {
      "id": "O0.3",
      "description": "serve refuses a non-loopback host",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" host_refusal",
      "check_timeout": 90,
      "constraint_text": ""
    },
    {
      "id": "O0.4",
      "description": "hub.css carries the exact rimer-ui token set (light+dark), no other hex colors",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" tokens",
      "check_timeout": 30,
      "constraint_text": ""
    },
    {
      "id": "O0.5",
      "description": "scripts/hub.ps1 is pure ASCII",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" -c \"import sys;d=open(r'D:\\Projects\\Music-AI-Toolshop\\scripts\\hub.ps1','rb').read();sys.exit(1 if any(b>127 for b in d) else 0)\"",
      "check_timeout": 30,
      "constraint_text": ""
    },
    {
      "id": "O0.6",
      "description": "skeleton tests pass",
      "check_command": "cd /d D:\\Projects\\Music-AI-Toolshop && \"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" -m pytest \"D:\\Projects\\Music-AI-Toolshop\\tests\\test_hub_skeleton.py\" -q -p no:cacheprovider",
      "check_timeout": 300,
      "constraint_text": ""
    },
    {
      "id": "O1.1",
      "description": "collector/receipt/store/index tests pass (all 4 receipt states, both session schemes, all ledger shapes, git allow-list)",
      "check_command": "cd /d D:\\Projects\\Music-AI-Toolshop && \"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" -m pytest \"D:\\Projects\\Music-AI-Toolshop\\tests\\test_hub_collectors.py\" \"D:\\Projects\\Music-AI-Toolshop\\tests\\test_hub_receipts.py\" \"D:\\Projects\\Music-AI-Toolshop\\tests\\test_hub_store.py\" \"D:\\Projects\\Music-AI-Toolshop\\tests\\test_hub_index.py\" -q -p no:cacheprovider",
      "check_timeout": 900,
      "constraint_text": ""
    },
    {
      "id": "O1.2",
      "description": "[live] every collector is ok on the real workspace",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" collectors_ok",
      "check_timeout": 120,
      "constraint_text": ""
    },
    {
      "id": "O1.3",
      "description": "[live] indexed commits/sessions/handoffs/listen verdicts reconcile exactly with independent counts",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" counts",
      "check_timeout": 600,
      "constraint_text": ""
    },
    {
      "id": "O1.4",
      "description": "[live] receipts match an independent re-implementation on >=5 real documents",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" receipts",
      "check_timeout": 600,
      "constraint_text": ""
    },
    {
      "id": "O1.5",
      "description": "[live] POST with a foreign Origin is refused (403)",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" origin_guard",
      "check_timeout": 300,
      "constraint_text": ""
    },
    {
      "id": "O1.6",
      "description": "[live] indexing changes no repo's git status",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" no_mutation",
      "check_timeout": 600,
      "constraint_text": "If a live lane wrote during the check, re-run once; a second failure is a real failure."
    },
    {
      "id": "O2.1",
      "description": "route tests pass (anchors, copy, Origin guard, traversal, sort)",
      "check_command": "cd /d D:\\Projects\\Music-AI-Toolshop && \"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" -m pytest \"D:\\Projects\\Music-AI-Toolshop\\tests\\test_hub_routes.py\" -q -p no:cacheprovider",
      "check_timeout": 600,
      "constraint_text": ""
    },
    {
      "id": "O2.2",
      "description": "[live] header, freshness and degraded banner follow 04",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" s0_header s0a_health s0b_degraded",
      "check_timeout": 120,
      "constraint_text": ""
    },
    {
      "id": "O2.3",
      "description": "[live] inbox column: count, order, limit, card copy follow 04",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" s1_inbox s1a_item s5_inbox_full",
      "check_timeout": 120,
      "constraint_text": ""
    },
    {
      "id": "O2.4",
      "description": "[live] inbox round trip: CLI ask -> Home -> UI resolve -> CLI list reads answer; file append-only",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" inbox_roundtrip",
      "check_timeout": 400,
      "constraint_text": ""
    },
    {
      "id": "O2.5",
      "description": "[live] journal: newest-first, <=100 rows = API, filters, row anatomy",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" s2_journal s2a_filters s2b_day s2c_row",
      "check_timeout": 300,
      "constraint_text": ""
    },
    {
      "id": "O2.6",
      "description": "[live] receipt badges on every session/handoff row and nowhere else",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" s2d_receipt",
      "check_timeout": 300,
      "constraint_text": ""
    },
    {
      "id": "O2.7",
      "description": "[live] /file serves workspace files only (404 outside)",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" file_guard",
      "check_timeout": 60,
      "constraint_text": ""
    },
    {
      "id": "O2.8",
      "description": "tokens still exact after UI work",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" tokens",
      "check_timeout": 30,
      "constraint_text": ""
    },
    {
      "id": "O3.1",
      "description": "repo_state tests pass",
      "check_command": "cd /d D:\\Projects\\Music-AI-Toolshop && \"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" -m pytest \"D:\\Projects\\Music-AI-Toolshop\\tests\\test_hub_repo_state.py\" -q -p no:cacheprovider",
      "check_timeout": 600,
      "constraint_text": ""
    },
    {
      "id": "O3.2",
      "description": "[live] repo table numbers equal git status for the first 3 repos",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" s3_repos s3b_lanes",
      "check_timeout": 300,
      "constraint_text": ""
    },
    {
      "id": "O3.3",
      "description": "[live] orchestrator marker overrides listed 1:1",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" s3a_marker",
      "check_timeout": 60,
      "constraint_text": ""
    },
    {
      "id": "O3.4",
      "description": "[live] header pills equal /api/repos sums and the ACTIVE marker",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" s0a_pills",
      "check_timeout": 120,
      "constraint_text": ""
    },
    {
      "id": "O4.1",
      "description": "artist collector + sanitiser tests pass",
      "check_command": "cd /d D:\\Projects\\Music-AI-Toolshop && \"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" -m pytest \"D:\\Projects\\Music-AI-Toolshop\\tests\\test_hub_artists.py\" -q -p no:cacheprovider",
      "check_timeout": 600,
      "constraint_text": ""
    },
    {
      "id": "O4.2",
      "description": "[live] Tale profile card: f0 mean matches json, de-esser reads linear",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" s4b_profile",
      "check_timeout": 120,
      "constraint_text": ""
    },
    {
      "id": "O4.3",
      "description": "[live] Tale chain maps: one figure per chain_map*.svg, no script",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" s4c_chainmaps",
      "check_timeout": 120,
      "constraint_text": ""
    },
    {
      "id": "O4.4",
      "description": "/mix_svg_tree SKILL points at artists/<name>/rounds/",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" skill_path",
      "check_timeout": 30,
      "constraint_text": ""
    },
    {
      "id": "O4.5",
      "description": "[live] artist grid, Tale songs table and ledgers match the files",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\" s4_artist_grid s4a_songs s4e_ledgers",
      "check_timeout": 120,
      "constraint_text": ""
    },
    {
      "id": "O5.1",
      "description": "inbox.jsonl is in backup coverage (test asserts manifest)",
      "check_command": "cd /d D:\\Projects\\Music-AI-Toolshop && \"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" -m pytest \"D:\\Projects\\Music-AI-Toolshop\\tests\\test_backup.py\" -q -p no:cacheprovider -k hub",
      "check_timeout": 600,
      "constraint_text": ""
    },
    {
      "id": "O5.2",
      "description": "the 'ask the hub' rule is in Toolshop, studio and MAirina AGENTS.md",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" -c \"import sys;fs=[r'D:\\Projects\\Music-AI-Toolshop\\AGENTS.md',r'D:\\Projects\\Music-AI-Toolshop\\studio\\AGENTS.md',r'D:\\Projects\\Music-AI-Toolshop\\MAirina_Tucc\\AGENTS.md'];sys.exit(0 if all('toolshop.hub ask' in open(f,encoding='utf-8').read() for f in fs) else 1)\"",
      "check_timeout": 30,
      "constraint_text": ""
    },
    {
      "id": "O5.3",
      "description": "full Toolshop suite has no failures (baseline 1965 passed / 1 skipped / 21 deselected, 2026-10-05)",
      "check_command": "cd /d D:\\Projects\\Music-AI-Toolshop && \"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" -m pytest \"D:\\Projects\\Music-AI-Toolshop\\tests\" -q -m \"not slow\" -p no:cacheprovider",
      "check_timeout": 3600,
      "constraint_text": ""
    },
    {
      "id": "O5.4",
      "description": "[live] every contract check passes",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" \"D:\\Projects\\Music-AI-Toolshop\\ORCHESTRATION\\hub\\checks\\contract_checks.py\"",
      "check_timeout": 1800,
      "constraint_text": ""
    },
    {
      "id": "O5.5",
      "description": "the hub lane worktree is clean before merge",
      "check_command": "\"D:\\Projects\\Music-AI-Toolshop\\.venv\\Scripts\\python.exe\" -c \"import subprocess,sys;o=subprocess.run(['git','-C',r'D:\\Projects\\Music-AI-Toolshop-wt-hub','status','--porcelain'],capture_output=True,text=True).stdout;sys.exit(1 if o.strip() else 0)\"",
      "check_timeout": 60,
      "constraint_text": ""
    }
  ],
  "constraints": [
    "No repo is mutated by indexing or serving (read-only git allow-list).",
    "The builder never edits ORCHESTRATION/hub/checks/contract_checks.py.",
    "Live OGCJ/OGCM lane files and Stemmeca_alatkka/stems/** are never written.",
    "No new third-party dependency beyond the hub extra (flask>=3.1); no CDN; no npm build.",
    "All work happens in the lane worktree D:\\Projects\\Music-AI-Toolshop-wt-hub on branch lane/hub."
  ],
  "baseline": {
    "test_count": 1965,
    "test_files": [],
    "skip_count": null,
    "lint_count": null,
    "file_count": null,
    "captured_at": "2026-10-05T19:00:00Z"
  },
  "spec_version": "0.1.0"
}
```
