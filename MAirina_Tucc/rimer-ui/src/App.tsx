import { useCallback, useEffect, useMemo, useState } from 'react'
import './App.css'
import { ApiError, api, type Settings } from './api'
import { Controls } from './components/Controls'
import { EditorRow } from './components/EditorRow'
import { Finder, type FinderTab } from './components/Finder'
import { StatsFooter } from './components/StatsFooter'
import { isLyricLine } from './text'
import type {
  AnchorsResponse,
  AtlasResponse,
  BanItem,
  CompareResponse,
  MeResponse,
  MultiResponse,
  RhymeResponse,
  Star,
  StatsResponse,
  XrayLine,
} from './types'

const STORE_KEY = 'mairina.draft.v1'
const DEFAULT_SETTINGS: Settings = {
  scheme: 'AABB',
  lines: 4,
  lane: 'drill',
  section: 'strofa',
  mode: 'rhyme',
  fresh: 0.5,
  artist: '',
  seed: '',
  dialect: 'ekavica',
}

interface Stored {
  draftId: string
  settings: Settings
  lines: string[]
  anchors: AnchorsResponse | null
}

type Engine = { state: 'ok' } | { state: 'offline' } | { state: 'corpus'; message: string }

function newDraftId(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `d-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

function loadStored(): Stored {
  try {
    const raw = localStorage.getItem(STORE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<Stored>
      const settings = { ...DEFAULT_SETTINGS, ...(parsed.settings ?? {}) }
      const lines = Array.isArray(parsed.lines) ? parsed.lines.map(String) : []
      return {
        draftId: typeof parsed.draftId === 'string' ? parsed.draftId : newDraftId(),
        settings,
        lines: resize(lines, settings.lines),
        anchors: parsed.anchors ?? null,
      }
    }
  } catch {
    /* storage unavailable or corrupt: start fresh */
  }
  return { draftId: newDraftId(), settings: DEFAULT_SETTINGS, lines: resize([], DEFAULT_SETTINGS.lines), anchors: null }
}

function isWarming(err: unknown): boolean {
  return err instanceof ApiError && err.status === 503 && /warming up/i.test(err.message)
}

function resize(lines: string[], n: number): string[] {
  return Array.from({ length: n }, (_, i) => lines[i] ?? '')
}

export default function App() {
  const [initial] = useState(loadStored)
  const [draftId] = useState(initial.draftId)
  const [settings, setSettings] = useState<Settings>(initial.settings)
  const [lines, setLines] = useState<string[]>(initial.lines)
  const [anchors, setAnchors] = useState<AnchorsResponse | null>(initial.anchors)
  const [busy, setBusy] = useState(false)
  const [engine, setEngine] = useState<Engine>({ state: 'ok' })

  const [xrayLines, setXrayLines] = useState<XrayLine[]>([])
  const [tab, setTab] = useState<FinderTab>('rhyme')
  const [rhyme, setRhyme] = useState<RhymeResponse | null>(null)
  const [multi, setMulti] = useState<MultiResponse | null>(null)
  const [compare, setCompare] = useState<CompareResponse | null>(null)
  const [atlas, setAtlas] = useState<AtlasResponse | null>(null)
  const [finderLoading, setFinderLoading] = useState(false)
  const [finderError, setFinderError] = useState<string | null>(null)
  const [votes, setVotes] = useState<Record<string, 1 | -1>>({})

  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [stars, setStars] = useState<Star[]>([])
  const [bans, setBans] = useState<BanItem[]>([])
  const [me, setMe] = useState<MeResponse | null>(null)
  const [saveStatus, setSaveStatus] = useState('')
  const [anchorNotes, setAnchorNotes] = useState<string[]>([])

  const text = lines.join('\n')

  // Persist the draft locally on every change (no network).
  useEffect(() => {
    try {
      const stored: Stored = { draftId, settings, lines, anchors }
      localStorage.setItem(STORE_KEY, JSON.stringify(stored))
    } catch {
      /* ignore quota / privacy-mode errors */
    }
  }, [draftId, settings, lines, anchors])

  const handleError = useCallback((err: unknown, toFinder = false) => {
    if (err instanceof ApiError) {
      if (err.kind === 'offline') return setEngine({ state: 'offline' })
      // The engine answers 503 "warming up" for ~20 s after start while it builds the corpus
      // atlas; that is not an outage, so it never raises the red engine banner.
      if (isWarming(err)) return toFinder ? setFinderError(err.message) : undefined
      if (err.kind === 'corpus') return setEngine({ state: 'corpus', message: err.message })
      if (toFinder) return setFinderError(err.message)
    }
    setFinderError(err instanceof Error ? err.message : 'Unexpected error')
  }, [])

  // Stats and stars are fast; the fingerprint (`me`) can take ~20 s the first time (it builds the
  // corpus atlas), so it is fetched on its own and never delays the footer or the ★ markers.
  const refreshSide = useCallback(async () => {
    const fast = Promise.all([api.stats(), api.stars(), api.bans()])
      .then(([s, st, b]) => {
        setStats(s)
        setStars(st.items)
        setBans(b.items)
        setEngine({ state: 'ok' })
      })
      .catch((err: unknown) => handleError(err))
    const slow = api
      .me(settings.lane)
      .then(setMe)
      .catch((err: unknown) => {
        if (isWarming(err)) window.setTimeout(() => void api.me(settings.lane).then(setMe).catch(() => undefined), 8000)
        else handleError(err)
      })
    await Promise.all([fast, slow])
  }, [settings.lane, handleError])

  const runXray = useCallback(
    async (body: string) => {
      if (!body.trim()) {
        setXrayLines([])
        return
      }
      try {
        const res = await api.xray(body, settings)
        setXrayLines(res.lines)
        setEngine({ state: 'ok' })
      } catch (err) {
        handleError(err)
      }
    },
    [settings, handleError],
  )

  // Initial side data, then whenever the lane changes.
  useEffect(() => {
    const t = window.setTimeout(() => void refreshSide(), 0)
    return () => window.clearTimeout(t)
  }, [refreshSide])

  // Debounced X-ray while typing (~400 ms).
  useEffect(() => {
    const t = window.setTimeout(() => void runXray(text), 400)
    return () => window.clearTimeout(t)
  }, [text, runXray])

  // Row index -> X-ray line (the engine numbers only lyric lines).
  const rowXray = useMemo(() => {
    const map = new Map<number, XrayLine>()
    let k = 0
    lines.forEach((line, i) => {
      if (isLyricLine(line) && k < xrayLines.length) map.set(i, xrayLines[k++])
    })
    return map
  }, [lines, xrayLines])

  const lyricNumber = useCallback(
    (row: number) => lines.slice(0, row + 1).filter(isLyricLine).length,
    [lines],
  )

  function changeSettings(patch: Partial<Settings>) {
    setSettings((cur) => ({ ...cur, ...patch }))
    if (patch.lines !== undefined) {
      const n = patch.lines
      setLines((cur) => resize(cur, n))
    }
  }

  async function newAnchors() {
    setBusy(true)
    try {
      const res = await api.anchors(settings)
      setAnchors(res)
      setAnchorNotes(res.warnings ?? [])
      setLines((cur) => resize(cur, Math.max(res.items.length, 1)))
      setSettings((cur) => ({ ...cur, lines: Math.max(res.items.length, 2) }))
      setEngine({ state: 'ok' })
      void refreshSide()
    } catch (err) {
      handleError(err, true)
    } finally {
      setBusy(false)
    }
  }

  // Re-roll only the unwritten anchors: every written line keeps its own end-word
  // (locked) and seeds its rhyme group's class with it.
  async function matchAnchors() {
    setBusy(true)
    try {
      const written = lines.map((l) => (isLyricLine(l) ? l : ''))
      const res = await api.anchors(settings, written)
      setAnchors(res)
      setAnchorNotes(res.warnings ?? [])
      setEngine({ state: 'ok' })
      void refreshSide()
    } catch (err) {
      handleError(err, true)
    } finally {
      setBusy(false)
    }
  }

  // Draw another member of the anchor's own rhyme class; null means it is exhausted.
  async function swapAnchor(row: number) {
    const anchor = anchors?.items[row]
    if (!anchor || anchor.locked) return
    try {
      const res = await api.swapAnchor(
        anchor.cls,
        anchor.group,
        (anchors?.items ?? []).map((a) => a.word),
        settings,
      )
      if (!res.item) {
        setAnchorNotes((cur) => [...cur, `${anchor.group}: class -${anchor.cls} exhausted — nothing left to swap in.`])
        return
      }
      setAnchors((cur) =>
        cur
          ? {
              ...cur,
              items: cur.items.map((a, i) => (i === row ? { ...a, ...res.item } : a)),
            }
          : cur,
      )
      setEngine({ state: 'ok' })
    } catch (err) {
      handleError(err, true)
    }
  }

  // Persist a ban, then swap the chip (the ban itself removes it from the class).
  async function banWord(word: string, row: number) {
    try {
      await api.ban(word)
      void refreshSide()
      await swapAnchor(row)
    } catch (err) {
      handleError(err, true)
    }
  }

  async function unbanWord(word: string) {
    try {
      await api.unban(word)
      void refreshSide()
    } catch (err) {
      handleError(err, true)
    }
  }

  async function rhymeQuery(word: string, lineText?: string) {
    setTab('rhyme')
    setFinderLoading(true)
    setFinderError(null)
    try {
      const row = lineText === undefined ? -1 : lines.indexOf(lineText)
      const target = row >= 0 ? rowXray.get(row)?.target?.median : undefined
      setRhyme(await api.rhyme(word, settings, lineText, target))
      setEngine({ state: 'ok' })
    } catch (err) {
      handleError(err, true)
    } finally {
      setFinderLoading(false)
    }
  }

  async function finderCall<T>(next: FinderTab, call: () => Promise<T>, set: (v: T) => void) {
    setTab(next)
    setFinderLoading(true)
    setFinderError(null)
    try {
      set(await call())
      setEngine({ state: 'ok' })
    } catch (err) {
      handleError(err, true)
    } finally {
      setFinderLoading(false)
    }
  }

  async function vote(listId: number, n: number, v: 1 | -1) {
    const key = `${listId}:${n}`
    const prev = votes[key]
    setVotes((cur) => ({ ...cur, [key]: v }))
    try {
      await api.vote(listId, [[n, v]])
      void refreshSide()
    } catch (err) {
      setVotes((cur) => {
        const copy = { ...cur }
        if (prev === undefined) delete copy[key]
        else copy[key] = prev
        return copy
      })
      handleError(err, true)
    }
  }

  async function starRow(row: number, tags: string[]) {
    try {
      await api.star(text, lyricNumber(row), tags, settings.lane, draftId)
      await refreshSide()
      void runXray(text)
    } catch (err) {
      handleError(err, true)
    }
  }

  async function unstar(id: number) {
    try {
      await api.unstar(id)
      await refreshSide()
      void runXray(text)
    } catch (err) {
      handleError(err, true)
    }
  }

  async function hintVote(ruleId: string, v: 1 | -1) {
    try {
      await api.hintVote(ruleId, v)
      void runXray(text)
      void refreshSide()
    } catch (err) {
      handleError(err, true)
    }
  }

  async function saveDraft() {
    try {
      const res = await api.used(text, draftId)
      setSaveStatus(`Saved · ${res.count} suggestion${res.count === 1 ? '' : 's'} used`)
      void refreshSide()
    } catch (err) {
      setSaveStatus('Saved locally only')
      handleError(err, true)
    }
  }

  const starByText = useMemo(() => {
    const map = new Map<string, Star>()
    stars.forEach((s) => map.set(s.text.trim(), s))
    return map
  }, [stars])

  return (
    <div className="app">
      <Controls
        settings={settings}
        busy={busy}
        canMatch={lines.some(isLyricLine)}
        onChange={changeSettings}
        onNewAnchors={() => void newAnchors()}
        onMatchAnchors={() => void matchAnchors()}
      />

      {engine.state === 'offline' && (
        <div className="banner" role="status">
          Engine not running. Start it: <code>MAirina_Tucc\mt.ps1 serve</code> — then{' '}
          <button type="button" className="btn" onClick={() => void refreshSide()}>
            Retry
          </button>
          . Your draft is safe in this browser.
        </div>
      )}
      {engine.state === 'corpus' && (
        <div className="banner error" role="alert">
          {engine.message}
        </div>
      )}

      <main className="main">
        <section className="card" aria-label="Verse editor">
          <div className="card-head">
            <span>
              You write every line. Double-click a word (or Alt+R) for rhymes; click an anchor for its rhymes.
            </span>
            {anchors?.target && (
              <span className="pill" title="Syllable range for this lane and section in real songs">
                target {anchors.target.approx ? '~' : ''}
                {anchors.target.lo}–{anchors.target.hi}
              </span>
            )}
          </div>
          {anchorNotes.length > 0 && (
            <div className="anchor-notes" role="status">
              {anchorNotes.map((w, i) => (
                <span key={i}>{w}</span>
              ))}
            </div>
          )}
          {lines.map((line, i) => (
            <EditorRow
              key={i}
              index={i}
              text={line}
              anchor={anchors?.items[i] ?? null}
              xray={rowXray.get(i) ?? null}
              star={starByText.get(line.trim()) ?? null}
              canStar={isLyricLine(line)}
              onText={(value) => setLines((cur) => cur.map((l, j) => (j === i ? value : l)))}
              onRhymeQuery={(word, lineText) => void rhymeQuery(word, lineText)}
              onStar={(tags) => void starRow(i, tags)}
              onUnstar={(id) => void unstar(id)}
              onHintVote={(ruleId, v) => void hintVote(ruleId, v)}
              onSwap={() => void swapAnchor(i)}
              onBan={(word) => void banWord(word, i)}
            />
          ))}
        </section>

        <Finder
          tab={tab}
          onTab={setTab}
          rhyme={rhyme}
          multi={multi}
          compare={compare}
          atlas={atlas}
          loading={finderLoading}
          error={finderError}
          votes={votes}
          onVote={(listId, n, v) => void vote(listId, n, v)}
          onRhymeQuery={(word) => void rhymeQuery(word)}
          onMultiQuery={(phrase) => void finderCall('multi', () => api.multi(phrase, settings), setMulti)}
          onCompare={(theme) =>
            void finderCall('compare', () => api.compare(settings.lane, settings.artist, theme, settings.dialect), setCompare)
          }
          onAtlas={() => void finderCall('atlas', () => api.atlas(settings.lane, settings.artist), setAtlas)}
        />
      </main>

      <StatsFooter
        stats={stats}
        me={me}
        starCount={stars.length}
        saveStatus={saveStatus}
        bans={bans}
        onSave={() => void saveDraft()}
        onUnban={(word) => void unbanWord(word)}
      />
    </div>
  )
}
