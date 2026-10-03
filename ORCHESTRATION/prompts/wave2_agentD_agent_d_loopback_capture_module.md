FRAMEWORK BOOTSTRAP (v13.0) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "Feasibility probe first (WASAPI loopback on default output), then toolshop/daw/loopback_capture.py + 'daw capture --seconds N [-o wav] [--play]'." --files "toolshop/daw/ + tests/test_daw_capture.py + pyproject.toml (+soundcard)".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: 1. pip install soundcard into .venv; verify loopback capture returns non-silent samples while system audio plays.
2. loopback_capture.py: record(seconds, sr=48000)->ndarray via soundcard loopback microphone; daw_cli 'capture --seconds N [-o out.wav] [--play]' (--play sends transport.play on the bridge port).
3. tests/test_daw_capture.py: mocked soundcard device, wav write, --play ordering.
4. Handoff: feasibility verdict (which driver mode Live uses if detectable), sample evidence (RMS/peak of probe capture), commands.
OPEN FILES: toolshop/daw/ + tests/test_daw_capture.py + pyproject.toml (+soundcard)

OUTPUT: Write your handoff to: ORCHESTRATION/fx_wave2/wave2/agent_d_handoff.md

CONSTRAINTS:
- FIRST task: 3s loopback feasibility capture. If Live uses exclusive ASIO -> record verdict + mitigation (shared WASAPI/MME or virtual cable) BEFORE building more.
- soundcard (MIT) into pyproject 'all' + 'daw' surface; license ledger note.
- Tests mock soundcard — no real audio in CI.
- Capture writes under data/toolshop/fx/ (data boundary) unless -o given.

CONTEXT BUDGET: 50k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
