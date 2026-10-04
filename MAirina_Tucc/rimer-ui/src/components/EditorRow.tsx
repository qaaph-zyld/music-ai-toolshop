import { useState } from 'react'
import type { AnchorItem, Star, XrayLine } from '../types'
import { lastWord, normalizeWord, syllableCount, wordAt } from '../text'

const PRESET_TAGS = ['metaphor', 'double-meaning', 'wordplay', 'punchline']
const GAUGE = ['▯▯▯', '▮▯▯', '▮▮▯', '▮▮▮']

interface Props {
  index: number
  text: string
  anchor: AnchorItem | null
  xray: XrayLine | null
  star: Star | null
  canStar: boolean
  onText: (value: string) => void
  onRhymeQuery: (word: string, lineText: string) => void
  onStar: (tags: string[]) => void
  onUnstar: (id: number) => void
  onHintVote: (ruleId: string, vote: 1 | -1) => void
  onSwap: () => void
  onBan: (word: string) => void
}

function sylClass(syl: number, xray: XrayLine | null): string {
  const t = xray?.target
  if (!t || syl === 0) return 'syl'
  if (syl < t.lo) return 'syl short'
  if (syl > t.hi) return 'syl over'
  return 'syl in'
}

export function EditorRow(props: Props) {
  const { index, text, anchor, xray, star, canStar } = props
  const [open, setOpen] = useState(false)
  const [menu, setMenu] = useState(false)
  const [tagging, setTagging] = useState(false)
  const [tags, setTags] = useState<string[]>([])
  const [freeTag, setFreeTag] = useState('')

  const syl = syllableCount(text)
  const hit = anchor !== null && normalizeWord(lastWord(text)) === normalizeWord(anchor.word)
  const target = xray?.target
  const targetLabel = target ? `${target.approx ? '~' : ''}${target.lo}–${target.hi}` : ''

  function queryAtCaret(input: HTMLInputElement) {
    const start = input.selectionStart ?? input.value.length
    const end = input.selectionEnd ?? start
    const selected = input.value.slice(start, end).trim()
    const word = selected && !/\s/.test(selected) ? selected : wordAt(input.value, start)
    if (word) props.onRhymeQuery(word, input.value)
  }

  function toggleTag(tag: string) {
    setTags((cur) => (cur.includes(tag) ? cur.filter((t) => t !== tag) : [...cur, tag]))
  }

  function submitStar() {
    const all = freeTag.trim() ? [...tags, freeTag.trim()] : tags
    props.onStar(all)
    setTagging(false)
    setTags([])
    setFreeTag('')
  }

  return (
    <div className="row">
      <div className="row-main">
        <span className="n">{index + 1}</span>
        <span className={sylClass(syl, xray)} title={target ? `target ${targetLabel} syllables` : 'syllables'}>
          {syl}
          {targetLabel && <span className="sr-only"> of target {targetLabel}</span>}
          {targetLabel && ` · ${targetLabel}`}
        </span>
        <input
          aria-label={`Line ${index + 1}${anchor ? `, should end on ${anchor.word}` : ''}`}
          placeholder={anchor ? `…end on “${anchor.word}”` : 'write your line'}
          value={text}
          onChange={(e) => props.onText(e.target.value)}
          onDoubleClick={(e) => queryAtCaret(e.currentTarget)}
          onKeyDown={(e) => {
            if (e.altKey && (e.key === 'r' || e.key === 'R')) {
              e.preventDefault()
              queryAtCaret(e.currentTarget)
            }
          }}
          spellCheck={false}
        />
        {anchor ? (
          <span className="anchor-wrap">
            <button
              type="button"
              className={anchor.locked ? 'anchor locked' : hit ? 'anchor hit' : 'anchor'}
              onClick={() => props.onRhymeQuery(anchor.word, text)}
              title={`${anchor.why} — click for rhymes`}
              aria-label={`Anchor ${anchor.group} ${anchor.word}${hit ? ', landed' : ''}. Show rhymes`}
            >
              <b>{anchor.group}</b>
              {anchor.word}
            </button>
            {!anchor.locked && (
              <button
                type="button"
                className="anchor-more"
                onClick={() => setMenu((v) => !v)}
                aria-expanded={menu}
                aria-label={`More actions for ${anchor.word}`}
                title="swap / ban"
              >
                ⋯
              </button>
            )}
            {menu && !anchor.locked && (
              <span className="anchor-menu" role="menu">
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setMenu(false)
                    props.onSwap()
                  }}
                  title="Another word from the same rhyme class"
                >
                  ↻ swap
                </button>
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setMenu(false)
                    props.onBan(anchor.word)
                  }}
                  title="Never suggest this word again (undo in the footer)"
                >
                  🚫 ban
                </button>
              </span>
            )}
          </span>
        ) : (
          <span />
        )}
        <div className="row-tools">
          {star ? (
            <button
              type="button"
              className="btn icon star on"
              onClick={() => props.onUnstar(star.id)}
              aria-label={`Unstar line ${index + 1}`}
              title={star.tags.length ? `★ ${star.tags.join(', ')}` : '★'}
            >
              ★
            </button>
          ) : (
            <button
              type="button"
              className="btn icon star"
              disabled={!canStar}
              onClick={() => setTagging((v) => !v)}
              aria-expanded={tagging}
              aria-label={`Star line ${index + 1}`}
            >
              ☆
            </button>
          )}
        </div>
      </div>

      {tagging && !star && (
        <div className="popover" role="group" aria-label={`Tags for line ${index + 1}`}>
          {PRESET_TAGS.map((t) => (
            <label key={t}>
              <input type="checkbox" checked={tags.includes(t)} onChange={() => toggleTag(t)} />
              {t}
            </label>
          ))}
          <input
            aria-label="Custom tag"
            placeholder="own tag"
            value={freeTag}
            onChange={(e) => setFreeTag(e.target.value)}
            size={10}
          />
          <button type="button" className="btn primary" onClick={submitStar}>
            Star
          </button>
          <button type="button" className="btn" onClick={() => setTagging(false)}>
            Cancel
          </button>
        </div>
      )}

      {xray && (
        <button
          type="button"
          className="meter"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-label={`Line ${index + 1} meter: rhyme ${xray.rhyme}, ${xray.devices.length} devices, ${xray.hints.length} hints. Toggle details`}
        >
          <span className="pill">rhyme {xray.rhyme}</span>
          <span className="pill gauge" title={`consonance ${xray.cons_density.toFixed(2)}`}>
            cons {GAUGE[Math.max(0, Math.min(3, xray.cons))]}
          </span>
          {xray.allit && <span className="pill">allit ✓</span>}
          {xray.devices
            // consonance and alliteration already have their own gauge / flag in this bar
            .filter((d) => d.confidence !== 'low' && d.kind !== 'consonance' && d.kind !== 'alliteration')
            .slice(0, 3)
            .map((d, i) => (
              <span key={`${d.kind}-${i}`} className="pill">
                ≈{d.kind.replace('_', ' ')}
              </span>
            ))}
          {xray.hints.length > 0 && <span className="pill hint">hints {xray.hints.length}</span>}
          {xray.vs_star && <span className="pill">vs★ {xray.vs_star}</span>}
        </button>
      )}

      {xray && open && (
        <div className="detail">
          {xray.assonance && <div>assonance: {xray.assonance}</div>}
          {xray.devices.length > 0 ? (
            <ul aria-label="Devices">
              {xray.devices.map((d, i) => (
                <li key={`${d.kind}-${i}`}>
                  {d.kind.replace('_', ' ')} — <i>{d.span}</i> ({d.confidence})
                </li>
              ))}
            </ul>
          ) : (
            <div>No devices detected (analysis only — your call).</div>
          )}
          {xray.hints.length > 0 && (
            <ul aria-label="Hints">
              {xray.hints.map((h) => (
                <li key={h.rule_id} className="hint-row">
                  <span>{h.label}</span>
                  <button
                    type="button"
                    className="btn icon"
                    onClick={() => props.onHintVote(h.rule_id, 1)}
                    aria-label={`Hint ${h.label} is useful`}
                  >
                    👍
                  </button>
                  <button
                    type="button"
                    className="btn icon"
                    onClick={() => props.onHintVote(h.rule_id, -1)}
                    aria-label={`Hint ${h.label} is wrong`}
                  >
                    👎
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
