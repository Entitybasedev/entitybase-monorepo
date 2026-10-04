import { test, expect } from '@playwright/test'
import { USER_ID } from './helpers.js'

/**
 * Create an item with a unique label and return its ID and label.
 * Uniqueness matters: search is asynchronous, so an old entity with the same
 * label could satisfy the assertion before this one is indexed.
 */
async function createItemWithLabel(request, label) {
  const res = await request.post(`${process.env.API_URL || 'http://localhost:8083'}/v1/entities/items`, {
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': USER_ID,
      'X-Edit-Summary': 'e2e search setup',
    },
    data: {
      type: 'item',
      labels: { en: { language: 'en', value: label } },
      descriptions: { en: { language: 'en', value: 'Created for the search e2e test' } },
      aliases: { en: [{ language: 'en', value: `${label} alias` }] },
    },
  })
  expect(res.ok()).toBeTruthy()
  const body = await res.json()
  const entityId = body.data?.entity_id ?? body.entity_id
  expect(entityId).toMatch(/^Q\d+$/)
  return { entityId, label }
}

async function createPropertyWithLabel(request, label) {
  const res = await request.post(
    `${process.env.API_URL || 'http://localhost:8083'}/v1/entities/properties`,
    {
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': USER_ID,
        'X-Edit-Summary': 'e2e search setup',
      },
      data: {
        type: 'property',
        datatype: 'wikibase-item',
        labels: { en: { language: 'en', value: label } },
      },
    }
  )
  expect(res.ok()).toBeTruthy()
  const body = await res.json()
  const entityId = body.data?.entity_id ?? body.entity_id
  expect(entityId).toMatch(/^P\d+$/)
  return { entityId, label }
}

async function search(page, term) {
  await page.getByTestId('search-input').fill(term)
  await page.getByTestId('search-submit').click()
}

test('search page is reachable from the menu and hints what can be searched', async ({
  page,
}) => {
  await page.goto('/')
  await page.getByTestId('nav-search').click()

  await expect(page.getByTestId('search-section')).toBeVisible()
  await expect(page.getByTestId('search-hint')).toBeVisible()
})

test('a created item turns up in search and links to its page', async ({ page, request }) => {
  const label = `E2E Searchable ${Date.now()}`
  const { entityId } = await createItemWithLabel(request, label)

  await page.goto('/search')
  await search(page, label)

  // Indexing is asynchronous: the worker picks the change off the stream
  const result = page
    .locator('[data-testid="search-result"]', { hasText: entityId })
    .first()
  await expect(result).toBeVisible({ timeout: 60000 })
  await expect(result.getByTestId('search-result-link')).toHaveText(label)
  await expect(result.getByTestId('search-result-type')).toHaveText('item')
  await expect(result.getByTestId('search-result-description')).toHaveText(
    'Created for the search e2e test'
  )

  await result.getByTestId('search-result-link').click()
  await expect(page.getByTestId('item-section')).toBeVisible()
  expect(page.url()).toContain(`/entity/${entityId}`)
})

test('a created property is found on the properties tab', async ({ page, request }) => {
  const label = `E2E Search Property ${Date.now()}`
  const { entityId } = await createPropertyWithLabel(request, label)

  await page.goto('/search')
  await page.getByTestId('search-type-property').click()
  await search(page, label)

  const result = page
    .locator('[data-testid="search-result"]', { hasText: entityId })
    .first()
  await expect(result).toBeVisible({ timeout: 60000 })
  await expect(result.getByTestId('search-result-type')).toHaveText('property')
})

test('an alias is searchable too', async ({ page, request }) => {
  const label = `E2E Alias Source ${Date.now()}`
  const alias = `${label} alternative`
  const { entityId } = await createItemWithLabel(request, label)

  await page.goto('/search')
  await search(page, alias)

  const result = page
    .locator('[data-testid="search-result"]', { hasText: entityId })
    .first()
  await expect(result).toBeVisible({ timeout: 60000 })
})

test('a query without matches says so', async ({ page }) => {
  await page.goto('/search')
  await search(page, `nothingmatches${Date.now()}`)

  await expect(page.getByTestId('search-no-results')).toBeVisible({ timeout: 30000 })
})

test('the query and the type filter are shareable in the URL', async ({ page, request }) => {
  const label = `E2E Shareable ${Date.now()}`
  await createItemWithLabel(request, label)

  await page.goto('/search')
  await page.getByTestId('search-type-lexeme').click()
  await search(page, label)

  await expect(page).toHaveURL(/q=/)
  await expect(page).toHaveURL(/type=lexeme/)

  // Reloading the shared URL runs the same search
  await page.reload()
  await expect(page.getByTestId('search-input')).toHaveValue(label)
})