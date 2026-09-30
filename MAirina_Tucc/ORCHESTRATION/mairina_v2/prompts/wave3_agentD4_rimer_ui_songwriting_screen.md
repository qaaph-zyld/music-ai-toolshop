FRAMEWORK BOOTSTRAP (v13.0) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "MAirina v2 wave 3 - rimer-ui React screen per approved mockup and frozen API contract" --files "D:/Projects/Music-AI-Toolshop/MAirina_Tucc/ORCHESTRATION/mairina_v2/ui_mockup.html, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/rimer-ui/src/App.tsx, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/rimer-ui/package.json, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/rimer-ui/vite.config.ts".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: 1. PRE-APPROVED design: the layout in MAirina_Tucc\ORCHESTRATION\mairina_v2\ui_mockup.html was approved by the user. Skip bootstrap step 5 for design, BUT see the npm gate below.
2. NPM GATE: rimer-ui has no node_modules. Before running `npm install` (from the existing package-lock.json, Cwd D:\Projects\Music-AI-Toolshop\MAirina_Tucc\rimer-ui) you MUST ask the user in chat and wait for an explicit yes. Do not add any new dependency beyond package.json.
3. Build the screen in rimer-ui/src (split into components under src/components/, API client in src/api.ts using the existing axios dependency): TOP controls bar (scheme, lines, lane, section, mode, fresh slider, artist, seed, 'New anchors'); LEFT editor = one row per line: line no, live syllable count vs target range (color: in range / short / over), text input, anchor chip at the end that turns green when the line ends on it, a compact METER BAR in the gutter (rhyme letter, cons gauge, allit, device icons, hint count) that expands on click to show details, a ★ button with a tag popover (metaphor, double meaning, wordplay, punchline, free text); RIGHT finder panel with tabs Rhymes | Multis | Compare | Atlas - ranked items with score bar, 'why' text, 👍/👎; clicking a word in the editor or an anchor chip queries rhymes for it (use the line text as context); hint rows in the expanded meter have 👍/👎 (POST hint-vote); FOOTER stats (votes, 👍 rate, used, A/B status, muted rules). Save draft = POST used with the full text and store the draft in localStorage.
4. FROZEN API CONTRACT (implemented in parallel by agent D3; Vite already proxies /api to 127.0.0.1:8000): POST /api/anchors {scheme,lines,lane,mode,seed,fresh,artist,section}; POST /api/rhyme {word,line?,target?,lane,fresh,artist}; POST /api/multi {phrase,lane}; POST /api/xray {text,lane,section?} -> per line {n,syl,target,rhyme,cons,allit,assonance,devices[],hints[{rule_id,label}],vs_star?}; POST /api/vote {list_id,items:[[n,+1|-1]]}; POST /api/star {text,line_no,tags[],lane}; DELETE /api/star/<id>; GET /api/stars; GET /api/me?lane; GET /api/atlas?lane&artist; GET /api/compare?lane&artist&theme; POST /api/hint-vote {rule_id,vote}; POST /api/used {text}; GET /api/stats. List responses carry list_id, arm, items[] with 'why'. Errors: {error}.
5. If the API is unreachable, show one clear banner ('Start the engine: mt serve') - do NOT ship fake data. Debounce xray calls while typing (~400 ms). The UI never generates lyric text: no 'complete line' features.
6. Theme: dark and light via CSS variables (the mockup's tokens), usable at 1280px and 820px widths, keyboard accessible buttons with aria-labels.
7. VERIFY: `npm run build` and `npm run lint` pass (paste summaries); `npm run dev` starts; with D3's server running (if available) do one manual pass: new anchors, type a line, see xray meter, click a word -> rhymes, vote, star. Take a screenshot or describe exactly what you saw if screenshots are unavailable.
8. HANDOFF: components list, how each contract endpoint is used, build/lint output, the manual pass notes, deviations. Reply exactly: 'WAVE 3 UI DONE - handoff at <path>'.
OPEN FILES: D:/Projects/Music-AI-Toolshop/MAirina_Tucc/ORCHESTRATION/mairina_v2/ui_mockup.html, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/rimer-ui/src/App.tsx, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/rimer-ui/package.json, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/rimer-ui/vite.config.ts

OUTPUT: Write your handoff to: MAirina_Tucc/ORCHESTRATION/mairina_v2/wave3/D4_handoff.md

CONSTRAINTS:
- You MAY create/modify files ONLY under D:\Projects\Music-AI-Toolshop\MAirina_Tucc\rimer-ui\ (plus your handoff). Do NOT touch MAirina_Tucc\mairina\ (agent D3 owns the backend this wave).
- npm install only after the user's explicit yes in chat; no new dependencies; never copy node_modules from elsewhere.
- No git add/commit/checkout/switch/stash/reset. Absolute paths. Dev server: run it in the foreground in its own terminal and stop it when done.
- Product rule: the UI FINDS and ANALYZES; it never writes lyric lines.

CONTEXT BUDGET: 200k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
