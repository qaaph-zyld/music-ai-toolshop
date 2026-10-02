// Small client-side text helpers. The authoritative analysis comes from the engine (/api/xray);
// these only keep the editor responsive while typing.

const VOWELS = new Set(['a', 'e', 'i', 'o', 'u'])
const WORD_RE = /[\p{L}']+/gu

export function normalizeWord(word: string): string {
  return word
    .toLowerCase()
    .replace(/[’]/g, "'")
    .replace(/^[^\p{L}]+|[^\p{L}]+$/gu, '')
}

export function words(text: string): string[] {
  return text.match(WORD_RE) ?? []
}

export function lastWord(text: string): string {
  const all = words(text)
  return all.length ? all[all.length - 1] : ''
}

/** Word around a caret position (for double-click / Alt+R lookups). */
export function wordAt(text: string, pos: number): string {
  for (const m of text.matchAll(WORD_RE)) {
    const start = m.index ?? 0
    if (pos >= start && pos <= start + m[0].length) return m[0]
  }
  return lastWord(text)
}

/** Serbian syllables: vowels a e i o u, plus syllabic r (r with no adjacent vowel). */
export function syllableCountWord(word: string): number {
  const letters = Array.from(word.toLowerCase()).filter((c) => /\p{L}/u.test(c))
  let count = 0
  letters.forEach((c, i) => {
    if (VOWELS.has(c)) count += 1
    else if (c === 'r') {
      const left = i > 0 && VOWELS.has(letters[i - 1])
      const right = i < letters.length - 1 && VOWELS.has(letters[i + 1])
      if (!left && !right) count += 1
    }
  })
  return count
}

export function syllableCount(text: string): number {
  return words(text).reduce((sum, w) => sum + syllableCountWord(w), 0)
}

/** Lines the engine numbers (xray/star): non-blank and not a [section] header. */
export function isLyricLine(line: string): boolean {
  const t = line.trim()
  return t.length > 0 && !t.startsWith('[')
}
