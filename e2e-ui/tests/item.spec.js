import { test, expect } from '@playwright/test'
import { USER_ID, API_URL, createPropertyViaApi } from './helpers.js'

test('create a property via the UI', async ({ page }) => {
  const label = `E2E Property ${Date.now()}`

  await page.goto('/')

  await page.getByTestId('property-label-input').fill(label)
  await page.getByTestId('create-property-button').click()

  const itemSection = page.getByTestId('item-section')
  await expect(itemSection).toBeVisible()
  await expect(page.getByTestId('item-label')).toHaveText(label)

  // Property IDs are P-prefixed and persisted server-side
  const permalink = await page.getByTestId('item-permalink').getAttribute('href')
  expect(permalink).toMatch(/\?entity=P\d+$/)
})

test('create an item via the UI and see its label', async ({ page }) => {
  const label = `E2E Item ${Date.now()}`

  await page.goto('/')

  await page.getByTestId('item-label-input').fill(label)
  await page.getByTestId('user-id-input').fill(USER_ID)
  await page.getByTestId('create-item-button').click()

  const itemSection = page.getByTestId('item-section')
  await expect(itemSection).toBeVisible()
  await expect(page.getByTestId('item-label')).toHaveText(label)
})

test('create an item and add a statement via the UI', async ({ page, request }) => {
  const label = `E2E Item ${Date.now()}`

  const propertyId = await createPropertyViaApi(request)

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

test('backend reflects the created item via API', async ({ request }) => {
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

test('item history shows revisions, views an old revision and diffs it', async ({
  page,
  request,
}) => {
  const propertyId = await createPropertyViaApi(request)

  // Create item + statement through the UI (multiple revisions)
  const label = `E2E History ${Date.now()}`
  await page.goto('/')
  await page.getByTestId('item-label-input').fill(label)
  await page.getByTestId('create-item-button').click()
  await expect(page.getByTestId('item-section')).toBeVisible()

  await page.getByTestId('statement-property-input').fill(propertyId)
  await page.getByTestId('statement-value-input').fill('Q5')
  await page.getByTestId('add-statement-button').click()
  await expect(page.getByTestId('statement').first()).toBeVisible()

  // History shows at least two revisions
  const rows = page.getByTestId('history-row')
  await expect(rows.first()).toBeVisible()
  expect(await rows.count()).toBeGreaterThanOrEqual(2)

  // View an old revision
  await page.getByTestId('history-view').first().click()
  await expect(page.getByTestId('revision-banner')).toBeVisible()
  await page.getByTestId('back-to-current').click()
  await expect(page.getByTestId('revision-banner')).toHaveCount(0)

  // Diff the newest revision against the previous one
  await page.getByTestId('history-diff').first().click()
  const diffView = page.getByTestId('diff-view')
  await expect(diffView).toBeVisible()
  await expect(diffView.locator('[data-testid="diff-added"]').first()).toContainText(
    propertyId
  )
})
