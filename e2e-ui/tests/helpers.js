import { expect } from '@playwright/test'

export const USER_ID = process.env.E2E_USER_ID || '90001'
export const API_URL = process.env.API_URL || 'http://localhost:8083'
// The wiki is part of the docker stack, not of the mock setup
export const DOKUWIKI_URL = process.env.DOKUWIKI_URL || 'http://localhost:8082'

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
 * Create an item via the API, to be the target of a statement.
 *
 * The API rejects a statement whose value names an entity that does not
 * exist, so a test that adds an item-valued statement needs a real target.
 * The instance is not seeded - nothing but what the tests create exists - so
 * the id has to come from here rather than being written down as Q5.
 *
 * POST /v1/entities/items takes no body and assigns the id itself, so this
 * makes an empty item and labels it as a second request.
 */
export async function createItemViaApi(request, label = 'target item') {
  const created = await request.post(`${API_URL}/v1/entities/items`, {
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': USER_ID,
      'X-Edit-Summary': 'e2e setup item',
    },
  })
  expect(created.ok()).toBeTruthy()
  const createdBody = await created.json()
  const itemId = createdBody.data?.entity_id ?? createdBody.entity_id
  expect(itemId).toMatch(/^Q\d+$/)

  const labelled = await request.put(`${API_URL}/v1/entities/${itemId}/labels/en`, {
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': USER_ID,
      'X-Edit-Summary': 'e2e setup item label',
    },
    data: { language: 'en', value: label },
  })
  expect(labelled.ok()).toBeTruthy()
  return itemId
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
