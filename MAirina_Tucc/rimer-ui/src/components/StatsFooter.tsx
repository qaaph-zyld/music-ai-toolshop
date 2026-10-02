import type { MeResponse, StatsResponse } from '../types'

interface Props {
  stats: StatsResponse | null
  me: MeResponse | null
  starCount: number
  saveStatus: string
  onSave: () => void
}

export function StatsFooter({ stats, me, starCount, saveStatus, onSave }: Props) {
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
      <span className="spacer" />
      <span aria-live="polite">{saveStatus}</span>
      <button type="button" className="btn" onClick={onSave}>
        Save draft
      </button>
    </footer>
  )
}
