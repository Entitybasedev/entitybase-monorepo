import { test, expect } from '@playwright/test'
import { USER_ID } from './helpers.js'

const API_URL = process.env.API_URL || 'http://localhost:8083'

const EDIT_HEADERS = {
  'Content-Type': 'application/json',
  'X-User-ID': USER_ID,
  'X-Edit-Summary': 'e2e search setup',
}

function edit(request, path, method, data) {
  return request.fetch(`${API_URL}${path}`, { method, headers: EDIT_HEADERS, data })
}

async function createEntity(request, kind) {
  // A property must say what type it is; items need nothing
  const body =
    kind === 'properties' ? { type: 'property', datatype: 'wikibase-item' } : undefined
  const res = await edit(request, `/v1/entities/${kind}`, 'POST', body)
  expect(res.ok()).toBeTruthy()
  const json = await res.json()
  return json.data?.entity_id ?? json.entity_id
}

async function setLabel(request, entityId, value) {
  const res = await edit(request, `/v1/entities/${entityId}/labels/en`, 'PUT', {
    language: 'en',
    value,
  })
  expect(res.ok()).toBeTruthy()
}

async function setDescription(request, entityId, value) {
  const res = await edit(request, `/v1/entities/${entityId}/descriptions/en`, 'PUT', {
    language: 'en',
    value,
  })
  expect(res.ok()).toBeTruthy()
}

async function setAliases(request, entityId, values) {
  // The endpoint takes a plain list of alias strings for the language
  const res = await edit(request, `/v1/entities/${entityId}/aliases/en`, 'PUT', values)
  expect(res.ok()).toBeTruthy()
}

/**
 * Create an item with a unique label and return its ID.
 *
 * The create endpoints make an *empty* entity, so the terms are set with one
 * request each afterwards - which is also what gets them into the search
 * index. Uniqueness matters: search is asynchronous, so an older entity with
 * the same label could satisfy an assertion before this one is indexed.
 */
async function createItemWithLabel(request, label, { description = '', aliases = [] } = {}) {
  const entityId = await createEntity(request, 'items')
  expect(entityId).toMatch(/^Q\d+$/)
  await setLabel(request, entityId, label)
  if (description) await setDescription(request, entityId, description)
  if (aliases.length) await setAliases(request, entityId, aliases)
  return entityId
}

async function createPropertyWithLabel(request, label) {
  const entityId = await createEntity(request, 'properties')
  expect(entityId).toMatch(/^P\d+$/)
  await setLabel(request, entityId, label)
  return entityId
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
  const entityId = await createItemWithLabel(request, label, {
    description: 'Created for the search e2e test',
  })

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
  const entityId = await createPropertyWithLabel(request, label)

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
  const entityId = await createItemWithLabel(request, label, { aliases: [alias] })

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