import { useState, type ReactNode } from 'react'
import type { AtlasResponse, AtlasRow, CompareResponse, MultiResponse, RhymeResponse } from '../types'

export type FinderTab = 'rhyme' | 'multi' | 'compare' | 'atlas'

interface ResultItem {
  n: number
  label: string
  score: number
  why: string
}

interface Props {
  tab: FinderTab
  onTab: (tab: FinderTab) => void
  rhyme: RhymeResponse | null
  multi: MultiResponse | null
  compare: CompareResponse | null
  atlas: AtlasResponse | null
  loading: boolean
  error: string | null
  votes: Record<string, 1 | -1>
  onVote: (listId: number, n: number, vote: 1 | -1) => void
  onRhymeQuery: (word: string) => void
  onMultiQuery: (phrase: string) => void
  onCompare: (theme: string) => void
  onAtlas: () => void
}

const TABS: { id: FinderTab; label: string }[] = [
  { id: 'rhyme', label: 'Rhymes' },
  { id: 'multi', label: 'Multis' },
  { id: 'compare', label: 'Compare' },
  { id: 'atlas', label: 'Atlas' },
]

function ResultList(props: {
  listId: number
  items: ResultItem[]
  votes: Record<string, 1 | -1>
  onVote: Props['onVote']
  onPick?: (label: string) => void
}) {
  const max = Math.max(...props.items.map((i) => i.score), 0.0001)
  if (props.items.length === 0) return <div className="empty">No results. Try another lane, a lower Fresh, or no artist filter.</div>
  return (
    <ol className="results">
      {props.items.map((item) => {
        const key = `${props.listId}:${item.n}`
        const v = props.votes[key]
        return (
          <li key={key}>
            <span className="n">{item.n}</span>
            <div>
              {props.onPick ? (
                <button type="button" className="w" onClick={() => props.onPick?.(item.label)} title="Show rhymes for this word">
                  {item.label}
                </button>
              ) : (
                <span className="w">{item.label}</span>
              )}
              <div className="bar" style={{ width: `${Math.max(4, Math.round((item.score / max) * 100))}%` }} />
              <div className="why">{item.why}</div>
            </div>
            <div className="votes">
              <button
                type="button"
                className={v === 1 ? 'btn icon on-up' : 'btn icon'}
                aria-pressed={v === 1}
                aria-label={`Good: ${item.label}`}
                onClick={() => props.onVote(props.listId, item.n, 1)}
              >
                👍
              </button>
              <button
                type="button"
                className={v === -1 ? 'btn icon on-down' : 'btn icon'}
                aria-pressed={v === -1}
                aria-label={`Bad: ${item.label}`}
                onClick={() => props.onVote(props.listId, item.n, -1)}
              >
                👎
              </button>
            </div>
          </li>
        )
      })}
    </ol>
  )
}

function AtlasTable({ rows, title }: { rows: AtlasRow[]; title: string }) {
  if (rows.length === 0) return null
  return (
    <div className="atlas-wrap">
      <table className="atlas">
        <caption className="sr-only">{title}</caption>
        <thead>
          <tr>
            <th scope="col">{title}</th>
            <th scope="col" title="lines">lines</th>
            <th scope="col" title="similes per 100 lines">simile</th>
            <th scope="col" title="anaphora per 100 lines">anaph</th>
            <th scope="col" title="strong alliteration per 100 lines">allit</th>
            <th scope="col" title="internal rhyme per 100 lines">intern</th>
            <th scope="col" title="multisyllabic share %">multi%</th>
            <th scope="col" title="median syllables per line">syl</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.scope}>
              <td>{r.scope}</td>
              <td>{r.lines}</td>
              <td>{r.simile.toFixed(1)}</td>
              <td>{r.anaphora.toFixed(1)}</td>
              <td>{r.allit.toFixed(1)}</td>
              <td>{r.internal.toFixed(1)}</td>
              <td>{r.multi_pct.toFixed(1)}</td>
              <td>{r.med_syl ?? '–'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function Finder(props: Props) {
  const [word, setWord] = useState('')
  const [phrase, setPhrase] = useState('')
  const [theme, setTheme] = useState('')

  let body: ReactNode = null
  if (props.tab === 'rhyme') {
    body = (
      <>
        <form
          className="finder-query"
          onSubmit={(e) => {
            e.preventDefault()
            if (word.trim()) props.onRhymeQuery(word.trim())
          }}
        >
          <input aria-label="Word to rhyme" placeholder={props.rhyme?.query ?? 'word (or double-click a word in a line)'} value={word} onChange={(e) => setWord(e.target.value)} />
          <button type="submit" className="btn">Rhymes</button>
        </form>
        {props.rhyme && (
          <ResultList
            listId={props.rhyme.list_id}
            items={props.rhyme.items.map((i) => ({ n: i.n, label: i.word, score: i.score, why: i.why }))}
            votes={props.votes}
            onVote={props.onVote}
            onPick={props.onRhymeQuery}
          />
        )}
      </>
    )
  } else if (props.tab === 'multi') {
    body = (
      <>
        <form
          className="finder-query"
          onSubmit={(e) => {
            e.preventDefault()
            if (phrase.trim()) props.onMultiQuery(phrase.trim())
          }}
        >
          <input aria-label="Ending phrase for multis" placeholder={props.multi?.query ?? 'ending, e.g. da me imaš'} value={phrase} onChange={(e) => setPhrase(e.target.value)} />
          <button type="submit" className="btn">Multis</button>
        </form>
        {props.multi && (
          <ResultList
            listId={props.multi.list_id}
            items={props.multi.items.map((i) => ({ n: i.n, label: i.phrase, score: i.score, why: i.why }))}
            votes={props.votes}
            onVote={props.onVote}
          />
        )}
      </>
    )
  } else if (props.tab === 'compare') {
    body = (
      <>
        <form
          className="finder-query"
          onSubmit={(e) => {
            e.preventDefault()
            props.onCompare(theme.trim())
          }}
        >
          <input aria-label="Theme for comparisons (optional)" placeholder="theme (optional), e.g. noć" value={theme} onChange={(e) => setTheme(e.target.value)} />
          <button type="submit" className="btn">ko / kao …</button>
        </form>
        {props.compare && (
          <ResultList
            listId={props.compare.list_id}
            items={props.compare.items.map((i) => ({ n: i.n, label: i.word, score: i.score, why: `${i.count}× after ko/kao · ${i.why}` }))}
            votes={props.votes}
            onVote={props.onVote}
            onPick={props.onRhymeQuery}
          />
        )}
      </>
    )
  } else {
    body = (
      <>
        <div className="finder-query">
          <span style={{ flex: 1 }}>Device rates in real songs (stats only)</span>
          <button type="button" className="btn" onClick={props.onAtlas}>
            Load
          </button>
        </div>
        {props.atlas && (
          <>
            <AtlasTable rows={props.atlas.lanes} title="lane" />
            <AtlasTable rows={props.atlas.artists} title="artist" />
          </>
        )}
      </>
    )
  }

  return (
    <aside className="card" aria-label="Finder">
      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={props.tab === t.id}
            onClick={() => props.onTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      {props.error && <div className="banner error" role="alert">{props.error}</div>}
      {props.loading && (
        <div className="empty" aria-live="polite">
          Searching…
          {(props.tab === 'compare' || props.tab === 'atlas') && (
            <div>This one reads the whole corpus — the first run can take up to ~20 s.</div>
          )}
        </div>
      )}
      {!props.loading && body}
    </aside>
  )
}
