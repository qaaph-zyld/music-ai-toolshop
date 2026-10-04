// Response/request shapes of the MAirina local API (127.0.0.1:8000, proxied as /api).
// Shared contract with mairina/api.py — keep both sides identical.

export type Lane = 'drill' | 'pop' | 'all'
export type Scheme = 'AABB' | 'ABAB' | 'AAAA' | 'ABBA'
export type Mode = 'rhyme' | 'assonance' | 'consonance'
export type Section = 'strofa' | 'refren' | 'prerefren' | 'postrefren' | 'hook' | 'bridge'
export type Dialect = 'ekavica' | 'all'
export type Arm = 'learned' | 'base'

export interface ListMeta {
  list_id: number
  arm: Arm
}

export interface AnchorItem {
  n: number
  group: string // scheme letter, e.g. "A"
  word: string
  upos: string
  cls: string // rhyme class, e.g. "-aka"
  freq: number
  why: string
  locked?: boolean // the user's own written end-word — not a suggestion
}
export interface AnchorsResponse extends ListMeta {
  target: TargetRange | null
  items: AnchorItem[]
  warnings?: string[] // seeded-group fallbacks, e.g. "A: 'seksi' has no rhyme partners — matched on assonance instead."
}

export interface SwapResponse {
  item: Omit<AnchorItem, 'n'> | null // null when the class is exhausted
  list_id: number | null
}

export interface BanItem {
  word: string
  ts: string
}
export interface BansResponse {
  items: BanItem[]
}

export interface RhymeItem {
  n: number
  word: string
  score: number
  kind: string // perfect-2 | perfect-1 | assonance | consonance
  why: string
}
export interface RhymeResponse extends ListMeta {
  query: string
  items: RhymeItem[]
}

export interface MultiItem {
  n: number
  phrase: string
  score: number
  why: string
}
export interface MultiResponse extends ListMeta {
  query: string
  items: MultiItem[]
}

export interface CompareItem {
  n: number
  word: string
  count: number
  score: number
  why: string
}
export interface CompareResponse extends ListMeta {
  items: CompareItem[]
}

export interface TargetRange {
  lo: number // p25
  median: number
  hi: number // p75
  approx: boolean // true when the lane x section had too few lines (fallback range)
}

export interface DeviceTag {
  kind: string
  span: string
  confidence: 'high' | 'medium' | 'low'
}

export interface HintTag {
  rule_id: string
  label: string
}

export interface XrayLine {
  n: number
  text: string
  syl: number
  target: TargetRange | null
  rhyme: string // letter or "-"
  cons: number // gauge level 0..3
  cons_density: number
  allit: boolean
  assonance: string | null
  devices: DeviceTag[]
  hints: HintTag[]
  vs_star: string | null
}
export interface XrayResponse {
  lines: XrayLine[]
}

export interface Star {
  id: number
  ts: string
  line_no: number
  text: string
  lane: Lane
  tags: string[]
}
export interface StarsResponse {
  items: Star[]
}

export interface FingerprintFeature {
  mean: number
  shrunk: number
  lane_mu: number | null
  lane_sigma: number | null
}
export interface MeResponse {
  n: number
  low_confidence: boolean
  numeric: Record<string, FingerprintFeature>
  tag_rates: Record<string, number>
  kind_rates: Record<string, number>
}

export interface AtlasRow {
  scope: string // "lane drill" or an artist slug
  lines: number
  simile: number
  anaphora: number
  allit: number
  internal: number
  code_switch: number
  name_drop: number
  multi_pct: number
  cons: number
  med_syl: number | null
}
export interface AtlasResponse {
  lanes: AtlasRow[]
  artists: AtlasRow[]
}

export interface HintVoteResponse {
  rule_id: string
  up: number
  down: number
  muted: boolean
}

export interface UsedResponse {
  count: number
  hits: string[]
}

export interface ArmStats {
  votes: number
  up_rate: number | null
}
export interface StatsResponse {
  votes: number
  up: number
  down: number
  up_rate: number | null
  used: number
  lists: number
  arms: Record<Arm, ArmStats>
  ab: string // e.g. "not enough data (12/100)"
  muted: string[]
}

export interface ApiErrorBody {
  error: string
}
