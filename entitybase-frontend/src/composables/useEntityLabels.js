// Resolves entity IDs to human-readable labels, cached per page load.
// Shared by the entity views: statements, lexeme language/category and
// form features all need to show a label for an ID.
import { ref } from 'vue'
import { getLabelWithFallback } from '../api.js'
import { fallbackChain, language } from '../settings.js'

export function useEntityLabels() {
  const cache = new Map()

  async function humanLabel(id) {
    if (!id) return ''
    if (cache.has(id)) return cache.get(id)
    const chain = [...new Set([language.value, ...fallbackChain.value])]
    let resolved = ''
    try {
      resolved = (await getLabelWithFallback(id, chain)) ?? ''
    } catch {
      resolved = ''
    }
    cache.set(id, resolved)
    return resolved
  }

  return { humanLabel }
}