import type { Settings } from '../api'
import type { Lane, Mode, Scheme, Section } from '../types'

const SCHEMES: Scheme[] = ['AABB', 'ABAB', 'AAAA', 'ABBA']
const LANES: Lane[] = ['drill', 'pop', 'all']
const SECTIONS: Section[] = ['strofa', 'refren', 'prerefren', 'postrefren', 'hook', 'bridge']
const MODES: Mode[] = ['rhyme', 'assonance', 'consonance']

interface Props {
  settings: Settings
  busy: boolean
  onChange: (patch: Partial<Settings>) => void
  onNewAnchors: () => void
}

export function Controls({ settings, busy, onChange, onNewAnchors }: Props) {
  return (
    <header className="controls">
      <h1>
        MAirina Tucc<small>finds, never writes — you write every line</small>
      </h1>
      <label className="field">
        Scheme
        <select value={settings.scheme} onChange={(e) => onChange({ scheme: e.target.value as Scheme })}>
          {SCHEMES.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </label>
      <label className="field">
        Lines
        <input
          type="number"
          min={2}
          max={16}
          value={settings.lines}
          onChange={(e) => onChange({ lines: Math.max(2, Math.min(16, Number(e.target.value) || 4)) })}
        />
      </label>
      <label className="field">
        Lane
        <select value={settings.lane} onChange={(e) => onChange({ lane: e.target.value as Lane })}>
          {LANES.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </label>
      <label className="field">
        Section
        <select value={settings.section} onChange={(e) => onChange({ section: e.target.value as Section })}>
          {SECTIONS.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </label>
      <label className="field">
        Mode
        <select value={settings.mode} onChange={(e) => onChange({ mode: e.target.value as Mode })}>
          {MODES.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </label>
      <label className="field">
        Fresh {settings.fresh.toFixed(1)}
        <input
          type="range"
          min={0}
          max={1}
          step={0.1}
          value={settings.fresh}
          onChange={(e) => onChange({ fresh: Number(e.target.value) })}
        />
      </label>
      <label className="field">
        Artist
        <input
          type="text"
          placeholder="e.g. devito"
          value={settings.artist}
          onChange={(e) => onChange({ artist: e.target.value.trim() })}
        />
      </label>
      <label className="field">
        Seed
        <input
          type="text"
          placeholder="e.g. panamera"
          value={settings.seed}
          onChange={(e) => onChange({ seed: e.target.value.trim() })}
        />
      </label>
      <button type="button" className="btn primary" onClick={onNewAnchors} disabled={busy}>
        {busy ? 'Finding…' : 'New anchors'}
      </button>
    </header>
  )
}
