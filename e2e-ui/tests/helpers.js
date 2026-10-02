import { expect } from '@playwright/test'

export const USER_ID = process.env.E2E_USER_ID || '90001'
export const API_URL = process.env.API_URL || 'http://localhost:8083'

/**
 * Create a property via the API. Statement adds validate that the
 * property entity exists, so tests that add statements must create
 * one first (property IDs are auto-enumerated, e.g. P30000).
 */
export async function createPropertyViaApi(request, label = 'instance of') {  const res = await request.post(`${API_URL}/v1/entities/properties`, {
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': USER_ID,
      'X-Edit-Summary': 'e2e setup property',
    },
    data: {
      type: 'property',
      datatype: 'wikibase-item',
      labels: { en: { language: 'en', value: label } },
    },
  })
  expect(res.ok()).toBeTruthy()
  const body = await res.json()
  const propertyId = body.data?.entity_id ?? body.entity_id
  expect(propertyId).toMatch(/^P\d+$/)
  return propertyId
}


/**
 * Read the entity ID from the current page URL. Entity pages live at
 * /entity/<qid> (older ?entity=<qid> links redirect there).
 */
export function entityIdFromUrl(page) {
  const path = new URL(page.url()).pathname
  const match = path.match(/\/entity\/([QPLE]\d+)/)
  return match ? match[1] : null
}

/**
 * Register a fresh account via the UI (registration logs the user in
 * immediately). Creating and editing requires being logged in.
 */
export async function registerViaUi(page) {
  for (let attempt = 0; attempt < 2; attempt++) {
    await page.goto('/register')
    await page
      .getByTestId('username-input')
      .fill(`e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`)
    await page.getByTestId('password-input').fill('e2e-password')
    await page.getByTestId('auth-submit').click()
    try {
      await page.waitForURL(/\/$/, { timeout: 10_000 })
      return
    } catch {
      // Registration failed (e.g. concurrent registration race); retry
      // with a fresh username
    }
  }
  throw new Error('registerViaUi: could not register after retries')
}
