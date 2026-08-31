# Plan — orchestration waves, continuing `2026-09-01-next-moves.md`

> Written 2026-09-01. State: `master` @ `ec2a43c`, **2 commits ahead of `origin/master`, unpushed.**
> Supersedes nothing — it is the *dispatch* layer for `2026-09-01-next-moves.md`, which stays the
> statement of intent. `[USER DECISION]` marks a step no agent may take unilaterally.

## The organising judgement

`next-moves.md` ordered the work correctly: **prove the lane on real input, make the corpus true,
remove the risk that could lose the corpus.** Nothing about that has changed. What has changed is
that its top item, **P0, is blocked on a human recording a vocal take** — and that block is not
something an agent can lift.

So the ordering here is not the plan's ordering. It is: **do everything P0 does not gate, arrange it
so P0 can be executed the minute the take exists, and refuse to let the blocked item stall the rest.**

Two further constraints shape the waves:

- **Every wave costs CPU on a machine that has one usable core-set and no usable GPU.** P1's corpus
  regeneration is ~25 h. It cannot overlap with anything else that measures time, because
  `AGENTS.md`'s measurement discipline requires a stable instrument. **The long batch runs alone.**
- **Cold subagents re-derive context.** Four parallel explorers each re-reading `AGENTS.md`, the
  roadmap and the plan is a real cost for shallow returns. Wave 1 is deliberately **two** agents with
  crisp, non-overlapping deliverables rather than a broad sweep.

---

## Wave 0 — close the inherited tree  ✅ DONE (orchestrator direct)

- [x] **Verified and committed the `production_analyzer` fix** carried uncommitted from a spawned
      agent's session across the handoff. Verified by reverting it — 3 of 10 tests fail without it —
      rather than accepting the handoff's assertion. `9027c6b`. Journal `J-001`.
- [x] **Created `docs/superpowers/JOURNAL.md`** — append-only findings record, seeded with eight
      carried findings tagged `unverified — source: <path>`. `ec2a43c`.
- [x] **Declared, not swept** (per scope discipline — these belong to other sessions, not this
      deliverable): `ORCHESTRATION/prompts/*` (hemija orchestration, complete — verdict *approved
      with 1 flagged FAIL*), `lyrics_research/documents/`, and untracked content inside the
      `mastering_tool` submodule.
- [ ] `[USER DECISION]` Push `9027c6b` + `ec2a43c` to `origin/master`.

---

## The journal contract — binding on every agent in every wave

The user's standing instruction for this orchestration is that **what we learn gets written down as
we learn it**, not reconstructed at close-out. `JOURNAL.md` is where it goes, and its rules are not
advisory:

| Rule | Why it exists |
|---|---|
| Each agent is assigned a **reserved `J-NNN` number range** before dispatch, and writes to its **own fragment** in `docs/superpowers/journal_inbox/`, never to `JOURNAL.md` directly. The orchestrator merges. | Reserved ranges stop *semantic* collision — two sessions once collided on CHANGELOG `#018`. But parallel agents appending to one file also collide *mechanically*: last writer wins and the other's entries vanish silently. A reserved range does not fix that; separate files do. |
| An entry needs **`Expected`** as well as `Found`. | A finding with no prior expectation is a note, not a finding. The delta *is* the content. |
| **Refuted hypotheses are mandatory entries**, not optional. | `J-000f` cost a full session to obtain. A negative result not written down gets re-bought. |
| Evidence is **first-hand or tagged `unverified — source: <path>`**. | `AGENTS.md`, verified-verdicts rule. Relayed numbers have already misled this project once. |
| The journal is appended **during** the work, not at the end. | A finding reconstructed at close-out is a memory of a finding. The hemija review found 3 factual errors in a handoff written exactly that way. |

---

## Wave 1 — two parallel explorers  ⏱ ~1 h wall, read-only  · GATE after

Neither agent needs a user ruling to start. Both produce a design a Wave 2 implementer can execute.

### Agent A — whisperX forced alignment: go / no-go  · journal range `J-010`–`J-019`

**Why this is first.** It does not merely *inform* blocking decision #3 (is 69% coverage acceptable),
it **shrinks it**. If forced alignment runs here, then 69% only ever mattered for the 444-track
corpus of *other people's* songs; for everything we write, the lyrics are already known and alignment
sidesteps the missing 31% entirely. A decision you can make smaller is better than a decision you
make well.

Deliverable: `docs/superpowers/specs/2026-09-01-forced-alignment-feasibility.md` + journal entries.
Read-only; **no installs** — the assessment must say what installing *would* cost, not incur it.

Must answer, each with evidence:
1. Does whisperX (alignment-only — no diarization, no HF token) install into the 3.11.9 venv
   **without network at run time**, and what does it pull in?
2. **The protobuf trap.** `pyproject.toml` records `classla==4.21.2`, `onnxruntime>=4.25.8`,
   `onnx-weekly>=6.31.1` as **mutually unsatisfiable** — one is always violated, currently
   onnxruntime's. Does whisperX add a fourth constraint, and does it collide? *This is the specific
   thing that can turn a go into a no-go, so it is not a footnote.*
3. What is the CPU cost per track, **estimated from the model size and the measured
   faster-whisper RTF of 1.09–1.17×** — stated as an estimate, not a measurement.
4. What does it need as input, and does `lyrics.db` already hold it for our own tracks?
5. Where does it sit relative to `specs/2026-07-15-oss-integration-map.md`, which already lists it.

### Agent B — dossier schema v2 and the migration that cannot lie  · journal range `J-020`–`J-029`

**Why this is first.** P1 is ~25 h of CPU. The design has to be right *before* the machine spends a
weekend, and `next-moves.md` names the exact failure mode: *"a batch that succeeds having skipped
half its input."*

Deliverable: `docs/superpowers/specs/2026-09-01-dossier-schema-v2.md` + journal entries. Read-only.

Must produce:
1. **Schema v2**, field by field, against the 444 existing dossiers — adding `key`/`mode` from K-S,
   `structure`, `beat_grid`, `premaster`, and `lyrics` from M5. Explicitly: what happens to the old
   `mode` that was a **loudness threshold**, and the `sections` that were always `[]`. A migration
   that silently reinterprets a field is worse than one that fails.
2. **The migration on `toolshop/batch.py`'s shared pattern** — status JSON flushed per item,
   `--limit`/`--offset`, skip-completed resume. Non-negotiable per `AGENTS.md`.
3. **The count verification**, designed as a deliverable in its own right: what query proves 444 in →
   444 out, and what it reports when the answer is 431.
4. **The 10–20 track sample protocol** and the diff format against the old dossiers — this is the
   gate before the weekend run, and it must be able to *fail*.

### Gate — human approval before Wave 2

Both specs read, both sets of journal entries reviewed. Blocking decision #3 is answerable here.

---

## Wave 1 — COMPLETE 2026-09-01. What it actually returned

Both agents came back, both deliverables written, the venv and the corpus untouched. Every
load-bearing claim was re-run by the orchestrator before merging — the spot-check tables are in
`JOURNAL.md` at each merge point. **Neither agent returned the answer its brief anticipated.**

**Agent A — GO, conditional**, on a sidecar venv, `whisperx==3.4.5`, and a `--require-alignment`
guard. But the verdict is the least interesting part:

- **`J-015` corrects P3's premise.** `align()` consumes segments already carrying `text`, `start`
  *and* `end` — it **refines a segmentation, it does not produce one**. It does **not** sidestep the
  31%; fed the ASR segmentation, the gap propagates. Closing it needs **a windowing layer we build**.
  Inside the covered 69% the win is real: correct words instead of guessed, ~20 ms frames instead of
  coarse spans.
- **`J-016`** — `lyrics.db` holds **none of our own material**: 1425 songs, all `corpus='genius-pro'`,
  `language` NULL on every row, **no audio join key**.
- **`J-014`** — there is **no `sr` alignment model**; `hr` is the proxy and `load_align_model` raises
  on unknown codes, so today's `DEFAULT_LANGUAGE="sr"` would crash.
- **`J-011`/`J-012`** — the real collision is **torch**, not protobuf. The protobuf trap the brief
  called the likely NO-GO **did not fire**.

> **So Wave 1 did not shrink blocking decision #3 — it sharpened it.** The brief's whole rationale
> for running A first was that forced alignment would route our own material around the 69%
> question. It does not. That question now has to be answered on its merits.

**Agent B — M6 resized, not designed.** The spec exists, but the finding that matters is that the
milestone as written could not have worked:

- **`J-024` is the headline.** `beat_grid`, `structure`, `premaster` and the K-S key block are
  emitted **only by `_basic_analysis`**, while the corpus batch hard-codes `backend="advanced"`.
  **A plain re-run would have added nothing** — and the count check would have reported a clean
  222 in / 222 out while doing it. **M6's blocker is a backend defect, not a batch run.**
- **`J-020`** — the corpus is **222 dossiers, not 444**. The glob `*_analysis.json` also matched the
  `_voice_analysis.json` sidecar. PapaPedro, the stated reason for revising 222 up to 444,
  contributes **no dossiers at all**.
- **`J-021`** — the cost inherits the same double count: **~13 h, an overnight**, not a weekend.
- **`J-025`** — the loudness-threshold `mode` is **live code**, not history: `feature_extractor.py:190`,
  yielding 215 major / 7 minor across the corpus.
- **`J-028`** — the corpus is **German**, and `transcribe.py` defaults to `language="sr"`,
  `model="small"` while every M5 number is `large-v3`.
- **`J-029`** — a `--limit 20` sample run would **overwrite `total_tracks`** in the corpus status
  file, destroying the baseline the count check compares against.

### What this does to Wave 2 and Wave 3

- **Wave 3's premise is gone.** There is no point scheduling a long batch until the backend emits the
  fields. Wave 3 is deferred behind a backend fix, and when it runs it is an **overnight**.
- **Wave 2's first item is no longer the migration.** It is: make the default backend emit the four
  fields, or make the batch use the backend that does — and decide which, because
  `_advanced_analysis` presumably exists for a reason.
- **`flow_analyzer` v2 keeps its Wave 2 slot** and its hard constraint (`J-000d`, no
  `Word.probability`), but its input story is now the windowing layer, not whisperX out of the box.

---

## Wave 2 — implementation  ⏱ days · gated

Contents depend on Wave 1's findings; the shape does not:

- **B's migration + sample validation** on 10–20 tracks, diffed and *reviewed*, before any full run.
- **A's forced-alignment adapter**, if A returns go. `--require-advanced`-style guard mandatory —
  `AGENTS.md` requires a fallback path be *declarable*, and this lane has an obvious silent fallback
  to plain ASR.
- **P4 sections consumers.** Sections have been emitted since `#048` and **nothing reads them**; T7
  Sample Forge auto-sectioning was deferred in `#018` precisely because the dossier emitted none —
  that reason is gone. Deferred to Wave 2 deliberately: it is P4, and value already paid for keeps.
- **P4 `flow_analyzer` v2** — beat grid × word timings. Deferred to Wave 2 because **its input source
  is A's answer.** Hard constraint, carried from `J-000d`: **do not weight or gate by
  `Word.probability`** — 0.836 mean probability while dropping 43% of the track.

## Wave 3 — the long batch  ⏱ ~25 h CPU, alone on the machine

Runs by itself. Nothing that measures time may run beside it. Counts verified before "done" is said.

---

## Blocked on the user, not on us

| # | Decision | Blocks | Can an agent proceed without it? |
|---|---|---|---|
| 1 | **Which Suno track, and who records the take** | **P0 — the highest-value item in the plan** | No. This is a person in a room with a microphone. |
| 2 | ~~DR target~~ **RULED 2026-09-01: a second copy in corresponding folders on `D:\Projects`.** | P2 | Yes — the target is now known and the work is unblocked. See the caveat below. |
| 3 | Is 69% coverage acceptable for flow v1 | P3, P4 | **Wave 1 Agent A is designed to shrink this decision rather than wait on it.** |
| 4 | Push the two Wave 0 commits | close-out | No. |

### Caveat on the G5 ruling, recorded once and then accepted

The ruling is a second copy in corresponding folders on `D:\Projects`. Stated plainly so the record
is not misleading: **this is redundancy, not disaster recovery.** It protects against accidental
deletion, an overwrite, and single-file corruption — all real and all worth having. It does not
protect against the failure `J-000h` was written about, which is the **2010 disk itself dying**, because
both copies are on that disk. G5 therefore stays **open as a risk** even once P2 ships.

Two things follow, and they are what makes the ruling worth executing rather than arguing with:

- The **Suno-coverage test is the more valuable half of P2 anyway** and is unaffected by the target.
  `backup.py` once verified clean for a month while collecting **zero** Suno data; a second copy of
  nothing is nothing. That test earns its keep on any target.
- The **restore test** is likewise unaffected. A copy that has never been restored is a hope.

**P0 remains the highest-value item here and this plan does not pretend otherwise.** Everything
below it is real work; none of it is a track. The wave structure exists so that the moment a take
exists, P0 runs against a lane whose other defects have been cleared — not so that P0 can be
postponed.
