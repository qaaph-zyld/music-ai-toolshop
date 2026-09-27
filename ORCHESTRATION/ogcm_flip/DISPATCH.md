# OGCM Flip — research wave dispatch card

Research-first rebuild of the failed July "2Pac — Only God Can Judge Me" drill flip (`Stemmeca_alatkka` lane). Four parallel web-research agents feed a synthesis gate; implementation waves (separation → chops → drums/808 → beat → vocal re-lay → master) follow only after the user approves the synthesis.

Plan: `D:\Projects\.workspace_archive\plans\ogcm-flip-research-first-rebuild.md`
Decisions locked by user (2026-09-27): chop-and-rebuild confirmed · same song, re-separate better · drums/808 extracted from the track · deliverable = new beat + 2Pac acapella re-laid over it.

## Paste order

Each file is a complete agent prompt — paste its contents (or "read this file and follow it exactly" + path) into a **separate** agent thread. All four can run fully in parallel — they are web-only researchers with disjoint topics.

| Slot | Agent | Spec file | Writes | Cost |
|---|---|---|---|---|
| 1 | R1 | `prompts\waveR_R1_separation.md` | `.workspace_archive\handoffs\researcher_ogcm_separation_<stamp>.md` | light |
| 2 | R2 | `prompts\waveR_R2_chop_rebuild.md` | `.workspace_archive\handoffs\researcher_ogcm_chop_rebuild_<stamp>.md` | light |
| 3 | R3 | `prompts\waveR_R3_drums_808.md` | `.workspace_archive\handoffs\researcher_ogcm_drums_808_<stamp>.md` | light |
| 4 | R4 | `prompts\waveR_R4_acapella_relay.md` | `.workspace_archive\handoffs\researcher_ogcm_acapella_relay_<stamp>.md` | light |

## Rules

- Researchers are **web-only** — no local file grepping, no code runs, no implementation decisions.
- Every claim needs a URL citation; conflicts between sources get surfaced, not resolved silently.
- Every handoff must end in the fenced YAML `findings` contract — reject a handoff that lacks it.
- Dependency note: R3 assumes R1 may deliver kit-piece drum separation; R4's vocal-grid pick and R2's tempo-map pick will be reconciled at synthesis — disagreement between them is expected input, not a bug.
- No git, no local writes outside the handoff file.

## Return to orchestrator

When all four handoffs land, say "ogcm research done" and I'll synthesize: verify the YAML contracts, reconcile R2's tempo-map pick against R4's vocal-grid pick, pick the separation stack, and freeze `.workspace_archive/plans/ogcm-flip-*.spec.md` for the approval gate.
