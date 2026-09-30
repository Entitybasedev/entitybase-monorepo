// User interface settings, persisted to localStorage.
import { ref, watch } from 'vue'

const LANGUAGE_KEY = 'entitybase.language'
const SHOW_QID_KEY = 'entitybase.showQid'

function loadStored(key, fallback) {
  try {
    return localStorage.getItem(key) ?? fallback
  } catch {
    return fallback
  }
}

export const SUPPORTED_LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'sv', name: 'Svenska' },
  { code: 'de', name: 'Deutsch' },
  { code: 'fr', name: 'Français' },
  { code: 'es', name: 'Español' },
  { code: 'nb', name: 'Norsk (bokmål)' },
  { code: 'da', name: 'Dansk' },
  { code: 'fi', name: 'Suomi' },
]

export const language = ref(loadStored(LANGUAGE_KEY, 'en'))
export const showQid = ref(loadStored(SHOW_QID_KEY, 'false') === 'true')

export const FALLBACK_CHAIN_KEY = 'entitybase.fallbackChain'
export const MAX_FALLBACK_LANGUAGES = 5

export const fallbackChain = ref(
  JSON.parse(loadStored(FALLBACK_CHAIN_KEY, '[]'))
)

watch(fallbackChain, (value) => {
  try {
    localStorage.setItem(FALLBACK_CHAIN_KEY, JSON.stringify(value))
  } catch {
    /* storage unavailable */
  }
}, { deep: true })

watch(language, (value) => {
  try {
    localStorage.setItem(LANGUAGE_KEY, value)
  } catch {
    /* storage unavailable */
  }
})

watch(showQid, (value) => {
  try {
    localStorage.setItem(SHOW_QID_KEY, String(value))
  } catch {
    /* storage unavailable */
  }
})
