// Typed client for the MAirina local API. Vite proxies /api -> http://127.0.0.1:8000 (same origin).
import axios, { AxiosError } from 'axios'
import type {
  AnchorsResponse,
  ApiErrorBody,
  AtlasResponse,
  BansResponse,
  CompareResponse,
  Dialect,
  HintVoteResponse,
  Lane,
  MeResponse,
  Mode,
  MultiResponse,
  RhymeResponse,
  Scheme,
  Section,
  Star,
  StarsResponse,
  StatsResponse,
  SwapResponse,
  UsedResponse,
  XrayResponse,
} from './types'

const http = axios.create({ baseURL: '/api', timeout: 30000 })

export type ApiErrorKind = 'offline' | 'corpus' | 'input' | 'server'

export class ApiError extends Error {
  kind: ApiErrorKind
  status: number | null

  constructor(kind: ApiErrorKind, message: string, status: number | null) {
    super(message)
    this.kind = kind
    this.status = status
  }
}

function toApiError(err: unknown): ApiError {
  if (err instanceof ApiError) return err
  const ax = err as AxiosError<ApiErrorBody>
  const status = ax.response?.status ?? null
  const body = ax.response?.data
  const message = body && typeof body === 'object' && 'error' in body ? body.error : ax.message
  // No response, or the Vite proxy answering because the engine is down.
  if (status === null || status === 502 || status === 504) {
    return new ApiError('offline', 'Engine not reachable', status)
  }
  if (status === 503) return new ApiError('corpus', message, status)
  if (status >= 400 && status < 500) return new ApiError('input', message, status)
  return new ApiError('server', message || 'Unexpected server error', status)
}

async function get<T>(url: string, params?: Record<string, string | undefined>): Promise<T> {
  try {
    const clean = Object.fromEntries(Object.entries(params ?? {}).filter(([, v]) => v !== undefined && v !== ''))
    return (await http.get<T>(url, { params: clean })).data
  } catch (err) {
    throw toApiError(err)
  }
}

async function post<T>(url: string, body: unknown): Promise<T> {
  try {
    return (await http.post<T>(url, body)).data
  } catch (err) {
    throw toApiError(err)
  }
}

async function del<T>(url: string): Promise<T> {
  try {
    return (await http.delete<T>(url)).data
  } catch (err) {
    throw toApiError(err)
  }
}

export interface Settings {
  scheme: Scheme
  lines: number
  lane: Lane
  section: Section
  mode: Mode
  fresh: number
  artist: string
  seed: string
  dialect: Dialect
}

export const api = {
  anchors: (s: Settings, written?: string[]) =>
    post<AnchorsResponse>('/anchors', {
      scheme: s.scheme,
      lines: written ? written.length : s.lines,
      lane: s.lane,
      mode: s.mode,
      seed: s.seed || null,
      fresh: s.fresh,
      artist: s.artist || null,
      section: s.section,
      dialect: s.dialect,
      written: written ?? null,
    }),
  swapAnchor: (cls: string, group: string, exclude: string[], s: Settings) =>
    post<SwapResponse>('/anchors/swap', {
      cls,
      group,
      mode: s.mode,
      lane: s.lane,
      fresh: s.fresh,
      artist: s.artist || null,
      dialect: s.dialect,
      exclude,
    }),
  ban: (word: string) => post<{ ok: boolean; word: string }>('/ban', { word }),
  unban: (word: string) => del<{ ok: boolean; word: string }>(`/ban/${encodeURIComponent(word)}`),
  bans: () => get<BansResponse>('/bans'),
  rhyme: (word: string, s: Settings, line?: string, target?: number) =>
    post<RhymeResponse>('/rhyme', {
      word,
      line: line || null,
      target: line && target ? target : null,
      lane: s.lane,
      fresh: s.fresh,
      artist: s.artist || null,
      dialect: s.dialect,
    }),
  multi: (phrase: string, s: Settings) =>
    post<MultiResponse>('/multi', { phrase, lane: s.lane, dialect: s.dialect }),
  xray: (text: string, s: Settings) => post<XrayResponse>('/xray', { text, lane: s.lane, section: s.section }),
  vote: (listId: number, items: [number, 1 | -1][]) => post<{ ok: boolean }>('/vote', { list_id: listId, items }),
  star: (text: string, lineNo: number, tags: string[], lane: Lane, draftId: string) =>
    post<Star>('/star', { text, line_no: lineNo, tags, lane, draft_id: draftId }),
  unstar: (id: number) => del<{ ok: boolean }>(`/star/${id}`),
  stars: () => get<StarsResponse>('/stars'),
  me: (lane: Lane) => get<MeResponse>('/me', { lane }),
  atlas: (lane: Lane, artist: string) => get<AtlasResponse>('/atlas', { lane, artist: artist || undefined }),
  compare: (lane: Lane, artist: string, theme: string, dialect: Dialect) =>
    get<CompareResponse>('/compare', { lane, artist: artist || undefined, theme: theme || undefined, dialect }),
  hintVote: (ruleId: string, vote: 1 | -1 | 0) => post<HintVoteResponse>('/hint-vote', { rule_id: ruleId, vote }),
  used: (text: string, draftId: string) => post<UsedResponse>('/used', { text, draft_id: draftId }),
  stats: () => get<StatsResponse>('/stats'),
}
