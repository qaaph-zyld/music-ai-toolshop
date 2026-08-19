# The Lyrics Popper Constitution

**Status: binding.** Every generated line is governed by these rules. A violation is not a stylistic note — it is a **reject-and-rewrite trigger**. The QC layer enforces what it can automatically; the rest is enforced by self-critique and the human gate.

Rules use **MUST**, **MUST NOT**, and **SHOULD**. Where a number is given, it is a gate, not a suggestion.

---

## Article 0 — The Prime Directive (supreme law)

**0.1** Every line MUST pass one test: *would this exact line, in real spoken Serbian, come from this specific persona's mouth on a real track?*

**0.2** If the honest answer is *"niko ovo ne bi rekao"* (nobody would actually say this), the line MUST be rewritten, regardless of how grammatically correct, clever, or "poetic" it is.

**0.3** No other article may be used to override Article 0. Fluency, rhyme, or rule-compliance never beats *would they say it.*

---

## Article 1 — Authenticity (real, spoken Serbian)

**1.1** Each song MUST declare one dialect — **ekavica** (Serbia) or **ijekavica** (Bosnia/Montenegro) — and hold it throughout. Mixing within a song is forbidden. (e.g. ekavica `lepo/vreme/dete` ↔ ijekavica `lijepo/vrijeme/dijete`.)

**1.2** Dialect MUST match the persona's region. A Belgrade persona does not sing ijekavica; a Sarajevo persona does not sing ekavica.

**1.3** Spoken contractions and elisions are **encouraged** where they serve sound and meter: `š'a, 'ajde, 'oću, ka'o, rek'o, doš'o, je l', nemo'`. They are not errors. Conversely, textbook-perfect full forms that no one sings (`Šta ćeš da radiš večeras` as a sung line) SHOULD be contracted.

**1.4** Idioms MUST be native Serbian. Calqued English idioms are forbidden (see Playbook §A for the banned list). Use `ludim za tobom`, not `padam za tobom`.

**1.5** Register MUST be consistent with the persona start to finish. No archaic/literary intrusions (`ljubljena, obasjava, čežnja`) into a modern club or drill voice, and no street slang dropped into a tender sevdah line, unless the persona explicitly code-switches.

---

## Article 2 — Concreteness (show, don't announce)

**2.1** Verses MUST carry concrete, sensory detail. **Concreteness density** (concrete sensory nouns ÷ abstract nouns) MUST be **≥ 1.5 per verse**.

**2.2** Emotions MUST NOT be announced where they can be shown. Banned as load-bearing content: bare declarations like `tako sam tužan/tužna`, `volim te toliko`, `srce me boli` **used as the substance of a line** rather than landed through an image. Show the cold coffee, the unanswered message, the empty side of the bed.

**2.3** Abstract-noun stacking is forbidden. A line MUST NOT lean on a pile of `ljubav / bol / sudbina / duša / sloboda / večnost / strast`. At most one such abstract per couplet, and only if anchored to something concrete.

**2.4** Each section (verse, chorus, bridge) MUST contain at least **one telling detail** — a specific object, place, time, gesture, or name — that could not have been written about a different song.

---

## Article 3 — Rhyme & Prosody (it has to sing)

**3.1 Lazy-rhyme cap.** Rhymes carried **only** by matching grammatical endings (`-ama, -ima, -ao, -la, -ću, -ti`) MUST NOT exceed **25%** of the song's rhymes. The rest MUST rhyme on roots/content, use slant rhyme, or rhyme across word boundaries.

**3.2** A word MUST NOT be rhymed with itself, nor with its own inflectional twin (e.g. `rukama / nogama` is weak; `očima / snovima` repeated is filler).

**3.3 Singability.** Every shipped line MUST scan against the song's stated tempo and phrase length without cramming or starving syllables. Lyrics are written to be *said out loud*; a line that only works on the page fails.

**3.4 Stress.** Line stresses SHOULD align with strong beats. In standard Serbian, stress never falls on the final syllable of a polysyllabic word — lines that force final-syllable emphasis to "land" a rhyme are a slop tell and MUST be reworked.

**3.5** Repetition MUST be earned. A repeated phrase MUST be worth repeating (a hook, a hypnotic club chant). Repetition used to fill bars is forbidden.

---

## Article 4 — Lexicon & Code-Switching

**4.1 English cap.** English tokens MUST stay within genre limits:
- Pop / tech-house: **≤ 15%** of tokens (≤ 20% only for an explicit bilingual hook gimmick).
- Hip-hop / trap / drill: **≤ 15%**, concentrated in brand names, ad-libs, and tags — **not** in narrative lines.
English MUST NOT carry narrative meaning in a verse unless the persona naturally code-switches.

**4.2 Banned globalized clichés.** The pop-cliché set is forbidden as imagery: burning flames of love, broken wings, eternal/undying love, "you complete me," stars/skies as stand-ins for feelings, rivers of tears. (Full list: Playbook §B.)

**4.3 Living lexicon.** Slang and turcizmi (`bre, faca, ekipa, lova, riba, mrak; merak, sevdah, dert, sokak, baksuz, džaba, komšija`) SHOULD be used where persona- and genre-appropriate — as native texture, never as sprinkled decoration to "sound Balkan."

**4.4** Invented or out-of-period slang is forbidden. Slang MUST be current and regionally real for the persona.

---

## Article 5 — Structure & Persona Fidelity

**5.1** Every song MUST be written *as a declared persona* (Craft KB §Personas). No persona, no draft.

**5.2** Point of view, addressee, verb tense, and dialect MUST stay consistent unless a deliberate shift is part of the design (and marked as such).

**5.3** Structure MUST follow the relevant genre module (Craft KB §Genre) and include the genre's signature moves where appropriate (the turn in the bridge, the drill beat-switch, the club drop chant). Verse-chorus sameness with no contrast between sections is forbidden: verses and chorus MUST differ in image density and rhythm.

**5.4** The hook MUST be the song's thesis — the most memorable phrase, present early (within the first ~60s of lyrics) and at least 3 times.

---

## Article 6 — Originality & Rights

**6.1** Output MUST NOT reproduce any line from the corpus. **Zero** reused hook lines. 4-gram overlap with `data/` corpus MUST be **< 2%** of lines; any single 4-gram match MUST be reviewed and removed unless it is genuinely common phrasing.

**6.2** The corpus is **calibration-only.** It is read to gauge authenticity and to anti-train (avoid overlap), never to copy from or to "blend."

**6.3** Generated work MUST NOT be a recognizable pastiche of one corpus artist. If a draft reads as "a fake [Artist] song," it fails originality.

**6.4** Corpus entries MUST retain source URL and attribution. Real lyrics are never redistributed; they exist here for analysis.

---

## Article 7 — Cultural & Ethical Handling

**7.1** Drill and trap may carry edge, swagger, and street menace — that is genre-authentic and MUST NOT be sanitized into toothlessness. But explicit, targeted threats of real-world violence, slurs, and content glorifying harm to real, identifiable people are out of bounds.

**7.2** Profanity is allowed as authentic emotional punctuation where the persona and genre warrant; it MUST NOT be used as filler shock. Mark explicit content.

**7.3** Ethnic, religious, and political references in the Balkan context MUST be handled with care; provocation for its own sake is forbidden. When in doubt, the human gate decides.

**7.4** Gender and relationship dynamics may reflect the scene's real attitudes (including bravado and heartbreak archetypes) without endorsing degradation; the line is the human gate's to draw.

---

## Article 8 — Enforcement (the gates)

A line/song is **shippable only after all gates pass.** In order:

1. **Self-critique gate.** The agent MUST run its draft against the [Anti-Slop Playbook](ANTI_SLOP_PLAYBOOK.md) smell-test and record what it checked and rewrote.
2. **Automated QC gate.** The QC slop-detector (scripts) MUST report: dialect consistency ✓, English ≤ cap, lazy-rhyme ≤ 25%, concreteness ≥ 1.5, originality < 2% overlap, zero banned-cliché hits. Any red = reject.
3. **Rubric gate.** The song MUST score within target on the authenticity/imagery/prosody/originality/singability/emotional-truth rubric (VISION §7).
4. **Human gate.** A native-speaker ear signs off. Mandatory through Phase 2. The human gate may reject on Article 0 alone, with no further justification required.

**8.1** If output fails a gate, the **output** is fixed — never the rule. A rule is changed only by the planner, on the record, with a changelog entry.

**8.2** "Reject triggers" (automatic, no debate): any calqued idiom from the banned list; any reused corpus hook line; dialect mixing; an abstract-only chorus; a line that fails Article 0 on the human ear.

---

## Amending this Constitution

This document is versioned. Changes are a **planner** decision, recorded with date, rationale, and the metric or example that motivated them. The executing agent proposes amendments in its task report; it does not edit the law to make a draft pass.

*Companion documents: [`VISION.md`](../VISION.md) · [`docs/ANTI_SLOP_PLAYBOOK.md`](ANTI_SLOP_PLAYBOOK.md) · [`docs/CRAFT_KB.md`](CRAFT_KB.md) · [`docs/ROADMAP.md`](ROADMAP.md).*
