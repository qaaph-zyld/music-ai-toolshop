# rimer-ui: MAirina Tucc writing screen

This is a React 19, Vite 8 and TypeScript screen for the MAirina engine. **It finds and analyzes; it never writes lyric lines.** It talks only to the local engine, through Vite's `/api` proxy to `http://127.0.0.1:8000`. There are no external services.

## Run

The normal way is `..\start.ps1`, which starts the engine and this screen and opens the browser. To run it by hand:

```powershell
# engine (terminal 1)
& "D:\Projects\Music-AI-Toolshop\MAirina_Tucc\mt.ps1" serve
# screen (terminal 2), from this folder
& ".\node_modules\.bin\vite.cmd" --port 5174 --strictPort --host 127.0.0.1
```

Port 5173 is often used by other local tools, which is why the screen is pinned to 5174.

## Install / build

```powershell
npm ci --legacy-peer-deps   # exactly the lockfile; --legacy-peer-deps because @tailwindcss/vite 4.2.1 declares vite<=7 while the project pins vite 8 (it builds fine)
npm run build                # tsc -b && vite build
npm run lint
```

`package.json` and `package-lock.json` are not changed by an install. `node_modules/` and `dist/` are gitignored.

## Layout

| File | Role |
|---|---|
| `src/types.ts` | The exact request and response shapes of the engine API. `mairina/api.py` follows them, and the contract tests in `MAirina_Tucc/tests/test_api.py` assert them |
| `src/api.ts` | Typed axios client. Errors are normalized to `offline` / `corpus` (503) / `input` (4xx) / `server` |
| `src/text.ts` | Client-side helpers for responsiveness only: syllable count, word at the caret. The engine's `/api/xray` is authoritative |
| `src/App.tsx` | State, the debounced X-ray (400 ms), the localStorage draft, votes, stars and hint votes |
| `src/components/` | `Controls`, `EditorRow` (line, syllables, anchor chip, meter, star popover), `Finder` (Rhymes / Multis / Compare / Atlas), `StatsFooter` |
