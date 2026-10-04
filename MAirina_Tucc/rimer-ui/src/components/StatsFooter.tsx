import { useState } from 'react'
import type { BanItem, MeResponse, StatsResponse } from '../types'

interface Props {
  stats: StatsResponse | null
  me: MeResponse | null
  starCount: number
  saveStatus: string
  bans: BanItem[]
  onSave: () => void
  onUnban: (word: string) => void
}

export function StatsFooter({ stats, me, starCount, saveStatus, bans, onSave, onUnban }: Props) {
  const [showBans, setShowBans] = useState(false)
  const rate = stats?.up_rate
  return (
    <footer className="footer" aria-label="Session stats">
      {stats ? (
        <>
          <span className="pill">
            Votes {stats.votes} · 👍 {rate === null || rate === undefined ? '–' : `${Math.round(rate * 100)}%`}
          </span>
          <span className="pill">Used {stats.used}</span>
          <span className="pill">A/B: {stats.ab}</span>
          {stats.muted.length > 0 && <span className="pill">Muted hints: {stats.muted.join(', ')}</span>}
        </>
      ) : (
        <span>No stats yet</span>
      )}
      <span className="pill">
        ★ {starCount}
        {me && me.low_confidence ? ' · fingerprint: low confidence (<10 ★)' : ''}
      </span>
      {bans.length > 0 && (
        <span className="pill bans-wrap">
          <button type="button" className="linklike" onClick={() => setShowBans((v) => !v)} aria-expanded={showBans}>
            Bans {bans.length}
          </button>
          {showBans && (
            <span className="bans-pop" role="list" aria-label="Banned words">
              {bans.map((b) => (
                <span key={b.word} className="ban-row" role="listitem">
                  {b.word}
                  <button
                    type="button"
                    className="btn icon"
                    onClick={() => onUnban(b.word)}
                    aria-label={`Unban ${b.word}`}
                    title="unban"
                  >
                    ×
                  </button>
                </span>
              ))}
            </span>
          )}
        </span>
      )}
      <span className="spacer" />
      <span aria-live="polite">{saveStatus}</span>
      <button type="button" className="btn" onClick={onSave}>
        Save draft
      </button>
    </footer>
  )
}
