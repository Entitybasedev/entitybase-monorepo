import { test, expect } from '@playwright/test'
import {
  USER_ID,
  API_URL,
  createPropertyViaApi,
  entityIdFromUrl,
  registerViaUi,
} from './helpers.js'

test('create a property via the UI', async ({ page }) => {
  await registerViaUi(page)
  const label = `E2E Property ${Date.now()}`

  await page.goto('/create-property')

  await page.getByTestId('property-label-input').fill(label)
  await page.getByTestId('create-property-button').click()

  const itemSection = page.getByTestId('item-section')
  await expect(itemSection).toBeVisible()
  await expect(page.getByTestId('item-label')).toHaveText(label)

  // Property IDs are P-prefixed and persisted server-side
  const permalink = await page.getByTestId('item-permalink').getAttribute('href')
  expect(permalink).toMatch(/\/entity\/P\d+$/)
})

test('an entity links to its history and its JSON and RDF data', async ({ page }) => {
  await registerViaUi(page)
  const label = `E2E Data Links ${Date.now()}`

  await page.goto('/create-item')
  await page.getByTestId('item-label-input').fill(label)
  await page.getByTestId('create-item-button').click()
  await expect(page.getByTestId('item-section')).toBeVisible()
  const entityId = entityIdFromUrl(page)

  await expect(page.getByTestId('item-history-link')).toHaveAttribute(
    'href',
    `/${entityId}/history`
  )

  // The API is served under the same origin as the UI
  const jsonHref = await page.getByTestId('item-json-link').getAttribute('href')
  expect(jsonHref).toBe(`/v1/entities/${entityId}.json`)
  const njsonHref = await page
    .getByTestId('item-njson-link')
    .getAttribute('href')
  expect(njsonHref).toBe(`/v1/entities/${entityId}.njson`)
  const rdfHref = await page.getByTestId('item-rdf-link').getAttribute('href')
  expect(rdfHref).toBe(`/v1/entities/${entityId}.ttl`)

  // Every representation is really served
  const jsonResponse = await page.request.get(jsonHref)
  expect(jsonResponse.ok()).toBeTruthy()
  // The revision is wrapped in a data envelope
  expect((await jsonResponse.json()).data.id).toBe(entityId)

  // The normalized revision has the hashes resolved, so the label is readable
  // straight out of it rather than being a reference to chase
  const njsonResponse = await page.request.get(njsonHref)
  expect(njsonResponse.ok()).toBeTruthy()
  expect((await njsonResponse.json()).labels.en.value).toBe(label)

  const rdfResponse = await page.request.get(rdfHref)
  expect(rdfResponse.ok()).toBeTruthy()
})

test('create an item via the UI and see its label', async ({ page }) => {
  await registerViaUi(page)
  const label = `E2E Item ${Date.now()}`

  await page.goto('/create-item')

  await page.getByTestId('item-label-input').fill(label)
  await page.getByTestId('create-item-button').click()

  const itemSection = page.getByTestId('item-section')
  await expect(itemSection).toBeVisible()
  await expect(page.getByTestId('item-label')).toHaveText(label)
})

test('create an item and add a statement via the UI', async ({ page, request }) => {
  await registerViaUi(page)
  const label = `E2E Item ${Date.now()}`

  const propertyId = await createPropertyViaApi(request)

  await page.goto('/create-item')

  // Create the item through the UI
  await page.getByTestId('item-label-input').fill(label)
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
  // Statements are grouped under an anchored property header. The header shows
  // the property's label, with its id on the anchor.
  const group = page.getByTestId('statement-group').first()
  await expect(group).toHaveAttribute('id', propertyId)
  await expect(group.getByTestId('statement-property')).toHaveText('instance of')
  await expect(group.getByTestId('statement-property')).toHaveAttribute(
    'title',
    propertyId
  )
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
  await registerViaUi(page)
  const propertyId = await createPropertyViaApi(request)

  // Create item + statement through the UI (multiple revisions)
  const label = `E2E History ${Date.now()}`
  await page.goto('/create-item')
  await page.getByTestId('item-label-input').fill(label)
  await page.getByTestId('create-item-button').click()
  await expect(page.getByTestId('item-section')).toBeVisible()
  const entityId = entityIdFromUrl(page)

  await page.getByTestId('statement-property-input').fill(propertyId)
  await page.getByTestId('statement-value-input').fill('Q5')
  await page.getByTestId('add-statement-button').click()
  await expect(page.getByTestId('statement').first()).toBeVisible()

  // History lives on its own page
  await page.getByTestId('item-history-link').click()
  await expect(page).toHaveURL(new RegExp(`/${entityId}/history$`))
  await expect(page.getByTestId('history-section')).toBeVisible()

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
