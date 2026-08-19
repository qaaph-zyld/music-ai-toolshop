# The Anti-Slop Playbook

The [Constitution](CONSTITUTION.md) says **what** is forbidden. This is the field manual for **spotting it and fixing it.** Keep it open while drafting.

Each entry: **Smell** (how to detect it) · **❌ Slop** (Serbian example) · **Why** · **✅ Fix** (Serbian example) · **Detector** (how QC catches it).

> All examples are in Latin script, ekavica, for illustration. The principle is dialect-agnostic.

---

## §A — Language & Idiom

### A1. Calqued idioms (English in a Serbian coat)
- **Smell:** the line maps word-for-word onto an English idiom.
- **❌ Slop:** *Padam za tobom svaki dan* (← "falling for you"). *Ti si moj ceo svet* (← "you're my whole world"). *Daj mi malo prostora* (← "give me space"). *Izgubljen u tvojim očima* (← "lost in your eyes").
- **Why:** these are English thoughts translated. A Serbian speaker reaches for different images entirely.
- **✅ Fix:** *Ludim za tobom, ne mogu da spavam.* *Bez tebe mi ništa ne valja.* *Pusti me malo da dišem.* *Ne mogu da te skinem s očiju.*
- **Detector:** banned-calque list (maintained in QC); any hit = reject.

### A2. Dialect mixing
- **Smell:** ekavica and ijekavica forms in the same song.
- **❌ Slop:** *Lepo* … two lines later … *lijepo*; *vreme* then *vrijeme*; *dete* then *dijete*.
- **Why:** instantly marks the writer as inauthentic; dialect is identity.
- **✅ Fix:** pick the persona's dialect and hold it. Belgrade → ekavica throughout. Sarajevo → ijekavica throughout.
- **Detector:** dialect-consistency check (paired form lists: lepo/lijepo, mleko/mlijeko, vreme/vrijeme, dete/dijete, …); any cross = reject.

### A3. Textbook over-correctness (no one sings like a grammar)
- **Smell:** every word in full, formal form; no contractions; lines too "correct" to sing.
- **❌ Slop:** *Šta ćeš da radiš ti večeras, hajde da idemo na žurku.*
- **Why:** sung Serbian elides and contracts. Full forms feel stiff and rarely scan.
- **✅ Fix:** *Š'a ćeš večeras? 'Ajde na splav.* / *Ka'o da te nešto muči, reci š'a 'oćeš.*
- **Detector:** flag sung lines with zero contractions and >9 tokens for a singability review (heuristic, human-confirmed).

### A4. Register collision
- **Smell:** literary/archaic words inside a modern club/drill voice, or street slang inside a tender line.
- **❌ Slop (club track):** *O ljubljena, tvoja milina obasjava ovu noć.*
- **Why:** `ljubljena/milina/obasjava` belong to a 19th-century poem, not a splav at 2 a.m.
- **✅ Fix:** *Mala, ti sijaš jače od neona, cela žurka gleda u tebe.*
- **Detector:** archaic/literary wordlist flagged against persona register.

---

## §B — Concreteness & Emotion

### B1. Abstract-noun stacking
- **Smell:** a line is mostly `ljubav / bol / sudbina / duša / sloboda / strast / večnost`.
- **❌ Slop:** *Ljubav, bol i sudbina, u mojoj duši tišina.*
- **Why:** vapor. Nothing to see, hear, or touch. Could be any song ever written.
- **✅ Fix:** *Tvoj broj još u telefonu, a ja ga ne zovem.*
- **Detector:** abstract-noun list; **concreteness density** = concrete sensory nouns ÷ abstract nouns must be ≥ 1.5 per verse.

### B2. Announced emotion (tell, don't show)
- **Smell:** the line states the feeling outright instead of landing it through a scene.
- **❌ Slop:** *Tako sam tužna bez tebe, srce me mnogo boli.*
- **Why:** the listener is told what to feel and feels nothing.
- **✅ Fix:** *Tvoja strana kreveta hladna već tri noći.* (We *deduce* the sadness — that's sevdah's whole engine.)
- **Detector:** flag bare-emotion templates (`tako sam {adj}`, `srce me boli`, `volim te toliko`) used as a line's whole substance.

### B3. Generic, placeless imagery
- **Smell:** "the city," "the night," "the lights" — nothing named.
- **❌ Slop:** *U gradu noćas svetla sijaju, a ja šetam sam.*
- **Why:** specificity is what makes a song *somebody's.* Generic = safe = slop.
- **✅ Fix:** *Na Adi do zore, kod onog splava, sam.* / *Kalemegdan, klupa, tri ujutru.*
- **Detector:** flag verses with zero proper nouns / specific objects (Constitution Art. 2.4 — one telling detail per section).

### B4. Globalized pop clichés
- **Smell:** imagery that belongs to no culture because it belongs to all of them.
- **❌ Slop:** *plamen ljubavi* (flame of love), *slomljena krila* (broken wings), *večna ljubav*, *reke suza* (rivers of tears), *ti si moje sunce*, stars-as-feelings.
- **Why:** these are the default settings of every AI and every karaoke ballad on earth.
- **✅ Fix:** trade the global cliché for a local concrete: not *reke suza* but *čaša koja se ne prazni*; not *ti si moje sunce* but *ti si mi i kafa i mamurluk.*
- **Detector:** banned-cliché list; any hit = reject.

---

## §C — Sound & Rhyme

### C1. Lazy grammatical rhyme
- **Smell:** consecutive lines rhyme only because they share a case/verb ending.
- **❌ Slop:** *Šetam ulicama / sanjam o rukama / plačem u snovima / davim se u rečima.* (`-ama / -ima` for free.)
- **Why:** Serbian inflection makes this rhyme cost nothing — and it sounds it.
- **✅ Fix:** rhyme on content/roots or use slant rhyme: *Šetam, a grad ćuti / nema te, ni traga / dišem, al' ko da spavam / svaki korak — vaga.*
- **Detector:** lazy-rhyme ratio (rhymes carried only by matching grammatical suffix) must be ≤ 25%.

### C2. Self-rhyme and inflectional twins
- **Smell:** a word rhymed with itself, or with its own grammatical sibling.
- **❌ Slop:** *…u mojim očima / …u tvojim očima*; *rukama / nogama* as a "rhyme."
- **Why:** it's repetition pretending to be rhyme.
- **✅ Fix:** find a true rhyme partner with a different root.
- **Detector:** identical-rhyme-word and same-lemma-rhyme check.

### C3. Lines that don't sing (page-only lines)
- **Smell:** reads fine silently; crams or starves syllables when said to a tempo.
- **❌ Slop:** a 14-syllable verse line forced over a 4-beat phrase built for 8.
- **Why:** lyrics are spoken/sung, not read. If it doesn't sit on the phrase, it's broken.
- **✅ Fix:** say every line out loud against the tempo; cut or contract until it sits. Use A3 contractions to hit the count.
- **Detector:** syllable-count vs. declared phrase-length per section; flag outliers for the read-aloud check.

### C4. Forced final-syllable stress
- **Smell:** a rhyme only "lands" if you stress the last syllable of a polysyllabic word.
- **❌ Slop:** bending *ljubav* to hit a beat on `-av`.
- **Why:** standard Serbian never stresses the final syllable of a polysyllable; forcing it is an audible tell.
- **✅ Fix:** rebuild the line so the natural stress falls on the beat; move the rhyme word.
- **Detector:** stress-position heuristic on rhyme words (human-confirmed).

---

## §D — Structure & Repetition

### D1. Mechanical filler repetition
- **Smell:** a phrase repeats to fill bars, not because it's a hook worth repeating.
- **❌ Slop:** repeating a forgettable line 4× because the section needed length.
- **Why:** repetition is a spotlight; pointing it at nothing wastes the song.
- **✅ Fix:** repeat only the line you'd want stuck in someone's head; build or vary on each pass (club: layer ad-libs; rap: switch the cadence).
- **Detector:** repeated-line analysis cross-checked against hook designation; repetition of non-hook lines flagged.

### D2. Verse/chorus sameness
- **Smell:** verse and chorus have the same image density and rhythm; no contrast.
- **❌ Slop:** a chorus that's just another verse line, no lift.
- **Why:** contrast is what makes a chorus *feel* like a chorus.
- **✅ Fix:** verses dense and specific; chorus shorter, chant-able, fewer tokens/line, one big image. (See Craft KB §Genre line-length targets.)
- **Detector:** compare avg tokens/line and concreteness between sections; near-identical = flag.

### D3. Weak or buried hook
- **Smell:** no single memorable phrase; or it arrives late and rarely.
- **❌ Slop:** the "hook" is abstract (*ljubav je sve što imam*) and shows up once.
- **Why:** the hook is the song's thesis and its survival mechanism.
- **✅ Fix:** make the hook concrete and chantable, land it within the first ~60s, repeat ≥ 3×, and make the *last* hook line the most memorable.
- **Detector:** hook presence/position/repetition check (already partly in `scripts/`).

---

## §E — Persona & Register

### E1. Faceless voice
- **Smell:** you can't say who is singing — age, gender, city, genre, attitude.
- **❌ Slop:** lyrics that would fit any artist = lyrics that fit none.
- **Why:** authenticity lives in a specific mouth (Constitution Art. 5.1, 0.1).
- **✅ Fix:** write *as* a declared persona (Craft KB §Personas); let their vocabulary fingerprint and "would never say" list shape every line.
- **Detector:** every generated song must reference a persona ID; missing = reject.

### E2. POV / tense drift
- **Smell:** "I" becomes "we" becomes "you"; past slides into present without intent.
- **❌ Slop:** verse in first person past, chorus randomly second person present.
- **Why:** the listener loses who's talking to whom.
- **✅ Fix:** lock POV, addressee, and tense; shift only by design and only at a structural seam.
- **Detector:** pronoun/tense tracking per section; unflagged shifts surfaced for review.

### E3. Decorative slang & turcizmi
- **Smell:** `bre`, `merak`, `sevdah` sprinkled in to "sound Balkan," not because the line needs them.
- **❌ Slop:** a tech-house lyric that suddenly drops *sevdah* for flavor.
- **Why:** native texture is load-bearing, not seasoning. Forced local color is its own slop.
- **✅ Fix:** use slang/turcizmi only where the persona would, doing real work in the line.
- **Detector:** density + persona-appropriateness check (human-confirmed).

---

## §F — Originality

### F1. Pastiche of a corpus artist
- **Smell:** the draft reads as "a fake [Angellina / Senidah / Nucci] song."
- **❌ Slop:** lifting a corpus artist's signature move, image set, and cadence wholesale.
- **Why:** the corpus is a compass, not a template (Constitution Art. 6.2–6.3).
- **✅ Fix:** absorb the *technique*, invent the *content*. Calibrate against the scene; don't impersonate one act.
- **Detector:** stylistic-overlap review at the human gate; high similarity to one artist = reject.

### F2. Corpus line reuse
- **Smell:** a line or hook is lifted (or barely altered) from a real song.
- **❌ Slop:** reusing a recognizable hook from `data/`.
- **Why:** copyright + originality. Zero tolerance.
- **✅ Fix:** write your own. If a 4-gram matches the corpus, change it unless it's genuinely common phrasing.
- **Detector:** n-gram overlap against `data/` corpus; 0 reused hooks, < 2% line overlap (Constitution Art. 6.1).

---

## The Slop Smell-Test (run on every draft, fast gut-check)

1. Could I point to the artist whose mouth this comes from? *(If no → E1.)*
2. Is there a calqued English idiom anywhere? *(→ A1.)*
3. Is the dialect consistent start to finish? *(→ A2.)*
4. Does each section have one specific, namable detail? *(→ B3, 2.4.)*
5. Am I announcing feelings I should be showing? *(→ B2.)*
6. Any globalized pop cliché (flames, wings, eternal love, rivers of tears)? *(→ B4.)*
7. Are more than a quarter of my rhymes free grammatical endings? *(→ C1.)*
8. Did I say every line out loud against the tempo — does it sit? *(→ C3.)*
9. Does the chorus actually contrast with the verse? *(→ D2.)*
10. Would a native speaker say *"niko ovo ne bi rekao"* about any line? *(→ Article 0.)*

Any "yes" to a problem (or "no" to 1/3/4/8/9) → **into the Rewrite Loop.**

## The Rewrite Loop

1. **Mark** every flagged line.
2. **Diagnose** with the §A–§F entry (what kind of slop is it?).
3. **Replace abstraction with a concrete image; replace calque with native idiom; replace free rhyme with content/slant rhyme.**
4. **Say it out loud** against the tempo.
5. **Re-run the smell-test.** Repeat until clean.
6. **Record** what you changed and why in the task report (self-critique gate).

*Companion documents: [`CONSTITUTION.md`](CONSTITUTION.md) · [`CRAFT_KB.md`](CRAFT_KB.md) · [`../VISION.md`](../VISION.md).*
