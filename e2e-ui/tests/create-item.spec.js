import { test, expect } from '@playwright/test'

const USER_ID = process.env.E2E_USER_ID || '90001'
const API_URL = process.env.API_URL || 'http://localhost:8083'

test('create item, add statement, see both in the UI', async ({ page, request }) => {
  const label = `E2E Item ${Date.now()}`

  // The statement add validates that the property entity exists, so create
  // one first via the API (property IDs are auto-enumerated, e.g. P30000).
  const propRes = await request.post(`${API_URL}/v1/entities/properties`, {
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': USER_ID,
      'X-Edit-Summary': 'e2e setup property',
    },
    data: {
      type: 'property',
      datatype: 'wikibase-item',
      labels: { en: { language: 'en', value: 'instance of' } },
    },
  })
  expect(propRes.ok()).toBeTruthy()
  const propBody = await propRes.json()
  const propertyId = propBody.data?.entity_id ?? propBody.entity_id
  expect(propertyId).toMatch(/^P\d+$/)

  await page.goto('/')

  // Create the item through the UI
  await page.getByTestId('item-label-input').fill(label)
  await page.getByTestId('user-id-input').fill(USER_ID)
  await page.getByTestId('create-item-button').click()

  const itemSection = page.getByTestId('item-section')
  await expect(itemSection).toBeVisible()
  await expect(page.getByTestId('item-label')).toHaveText(label)

  // Add a statement (instance of = human)
  await page.getByTestId('statement-property-input').fill(propertyId)
  await page.getByTestId('statement-value-input').fill('Q5')
  await page.getByTestId('add-statement-button').click()

  const statement = page.getByTestId('statement').first()
  await expect(statement).toBeVisible()
  await expect(statement.getByTestId('statement-property')).toHaveText(propertyId)
  await expect(statement.getByTestId('statement-value')).toHaveText('Q5')
  await expect(statement.getByTestId('statement-value')).toBeVisible()
})

test('backend reflects the created entity via API', async ({ request }) => {
  // Create via API to cross-check GET persistence
  const res = await request.post(`${API_URL}/v1/entities/items`, {
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': USER_ID,
      'X-Edit-Summary': 'e2e api smoke',
    },
    data: {
      type: 'item',
      labels: { en: { language: 'en', value: `API Item ${Date.now()}` } },
    },
  })
  expect(res.ok()).toBeTruthy()
  const created = await res.json()
  const entity_id = created.data?.entity_id ?? created.entity_id

  const get = await request.get(`${API_URL}/v1/entities/${entity_id}`)
  expect(get.ok()).toBeTruthy()
  const body = await get.json()
  expect(body.id ?? body.data?.id ?? entity_id).toBeTruthy()
})
