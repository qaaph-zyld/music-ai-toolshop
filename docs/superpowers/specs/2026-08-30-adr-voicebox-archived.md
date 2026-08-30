# ADR — Voicebox archived out of the repo

**Date:** 2026-08-30 · **Status:** Accepted
**Milestone:** H1-M5 (roadmap v2 §G3: *"Voicebox: archive out of repo in H1-M5 (ADR + upstream link)"*)
**Supersedes nothing. Records a removal that had already happened without its ADR.**

---

## Context

`Voicebox/` sat in this repo as a **fully vendored fork** — 410 tracked files — of an external
text-to-speech / voice-synthesis project. It was never wired into the `toolshop` package: no CLI verb,
no adapter, no import from any module under `toolshop/`. It was a parked lane awaiting the GPU gate.

Two things made the situation worse than idle weight:

1. **The records already claimed it was gone.** `PROJECTS_INDEX.md` described it as *"Vendored fork
   removed; re-clone when GPU gate opens"* while all 410 files were still tracked. A reader trusting
   the index would have been wrong about the repo's actual contents.
2. **It inflated every clone.** The repo carried a full upstream tree for a lane under explicit
   non-investment (roadmap §6, "Parked Lane").

The removal was executed in **P0 (2026-08-19, decision D9, CHANGELOG #040)** — `git rm -r --cached
Voicebox/`, with the directory added to `.gitignore`. Tracked files fell 2,256 → 1,859. **The ADR the
roadmap asked for was not written at the time.** This is that ADR, written late and saying so.

## Decision

**Voicebox is not part of this repo.** It is neither vendored nor submoduled. The working copy on this
machine remains on disk under `Voicebox/`, gitignored, so nothing was destroyed — consistent with the
standing rule that data and audio are moved or quarantined, never deleted.

## Rationale

- **Nothing depended on it.** No `toolshop` module imports it; removing it changed no behaviour and
  broke no test.
- **It is GPU-gated.** Compute is CPU-only by locked decision (roadmap §0). Voicebox cannot run
  usefully here until the GPU gate opens, so vendoring it buys nothing today.
- **Superseded as the likely path anyway.** The 2026-07-22 landscape research found **GPT-SoVITS**
  (CPU-fast, MIT, actively maintained) a better someday voice-synthesis route than Voicebox. Carrying
  a fork of the *less* likely choice is the weakest case of all.
- **Vendoring is the wrong mechanism regardless.** If this lane ever opens, the project's own
  convention is an adapter against an upstream dependency plus a licence-ledger entry — not a copied
  tree that silently drifts from upstream with no update path.

## Consequences

- Clones are smaller and `PROJECTS_INDEX.md` now matches reality.
- **The vendored copy is frozen at whatever upstream commit it was taken from, and that provenance was
  never recorded.** If the lane reopens, re-clone from upstream; do not resurrect the local copy.
- No licence-ledger entry exists for it, which is consistent with it not being a dependency.

## Re-adoption condition

Revisit only when **both** hold:

1. The GPU gate opens (roadmap §6 revisit triggers; goals v2 G9 — a used 8–12 GB card unlocks
   essentially the whole shelf).
2. A voice-synthesis lane is actually scheduled — at which point **evaluate GPT-SoVITS first**, per the
   gap-fill research. Voicebox is the fallback, not the default.

On re-adoption: fresh upstream clone, adapter pattern, licence-ledger entry, measured CPU/GPU cost.
Never re-vendor.

## Upstream

Recorded honestly: **the upstream URL was not captured before the files were untracked**, and the
vendored tree carries no remote of its own. The working copy still on disk under `Voicebox/voicebox/`
is the only local record. Anyone reopening this lane should identify upstream from that tree's own
metadata rather than trusting a URL reconstructed from memory here — a guessed link in an ADR is worse
than an admitted gap.
