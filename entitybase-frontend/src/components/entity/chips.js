// Chip-style list input helpers, shared by the alias editor and the lexeme
// form editor (grammatical features): a free-text draft is committed as chips,
// and blank or duplicate entries are dropped (first casing wins).

// Split a draft into candidate values: trim, drop blanks, dedupe
// case-insensitively.
export function parseChipDraft(draft) {
  const seen = new Set()
  const values = []
  for (const raw of String(draft ?? '').split(',')) {
    const value = raw.trim()
    if (!value) continue
    const key = value.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    values.push(value)
  }
  return values
}

// Append the draft's values to the current chips, skipping duplicates.
export function addChips(current, draft) {
  const values = Array.isArray(current) ? [...current] : []
  for (const value of parseChipDraft(draft)) {
    const exists = values.some((v) => v.toLowerCase() === value.toLowerCase())
    if (!exists) values.push(value)
  }
  return values
}