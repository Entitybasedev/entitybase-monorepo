// Authentication state, persisted to localStorage.
import { computed, ref } from 'vue'

const BASE = import.meta.env.VITE_API_BASE || ''

const TOKEN_KEY = 'entitybase.token'
const USER_ID_KEY = 'entitybase.userId'
const USERNAME_KEY = 'entitybase.username'

function loadStored(key) {
  try {
    return localStorage.getItem(key) ?? ''
  } catch {
    return ''
  }
}

function persist() {
  try {
    if (token.value) localStorage.setItem(TOKEN_KEY, token.value)
    else localStorage.removeItem(TOKEN_KEY)
    if (userId.value) localStorage.setItem(USER_ID_KEY, String(userId.value))
    else localStorage.removeItem(USER_ID_KEY)
    if (username.value) localStorage.setItem(USERNAME_KEY, username.value)
    else localStorage.removeItem(USERNAME_KEY)
  } catch {
    /* storage unavailable */
  }
}

export const token = ref(loadStored(TOKEN_KEY))
export const userId = ref(loadStored(USER_ID_KEY) ? Number(loadStored(USER_ID_KEY)) : 0)
export const username = ref(loadStored(USERNAME_KEY))

export const isLoggedIn = computed(() => token.value !== '' && userId.value > 0)

function safeJsonParse(text) {
  return JSON.parse(text)
}

function parseAuthBody(res, what) {
  if (!res.ok) {
    return res
      .text()
      .then((text) => {
        let message = text
        try {
          const parsed = JSON.parse(text)
          message = parsed.message ?? parsed.detail ?? text
        } catch {
          /* keep raw text */
        }
        throw new Error(`${what} failed: ${res.status} ${message}`)
      })
  }
  return res.text().then(safeJsonParse)
}

async function authenticate(path, credentials) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials),
  })
  const body = await parseAuthBody(res, `POST ${path}`)
  token.value = body.token
  userId.value = body.user_id
  username.value = body.username
  persist()
  return body
}

export async function login(user, password) {
  return authenticate('/v1/auth/login', { username: user, password })
}

export async function register(user, password) {
  return authenticate('/v1/auth/register', { username: user, password })
}

export function logout() {
  token.value = ''
  userId.value = 0
  username.value = ''
  persist()
}

export function authHeaders() {
  return token.value ? { Authorization: `Bearer ${token.value}` } : {}
}
