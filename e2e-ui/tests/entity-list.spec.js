import { test, expect } from '@playwright/test'
import { createPropertyViaApi, entityIdFromUrl, registerViaUi } from './helpers.js'

test('entity list is reachable from the menu and lists created entities', async ({
  page,
}) => {
  await registerViaUi(page)
  const label = `E2E List ${Date.now()}`

  // Create an item via the UI
  await page.goto('/create-item')
  await page.getByTestId('item-label-input').fill(label)
  await page.getByTestId('create-item-button').click()
  await expect(page.getByTestId('item-section')).toBeVisible()
  const entityId = entityIdFromUrl(page)
  expect(entityId).toMatch(/^Q\d+$/)

  // Find the page via the menu
  await page.getByTestId('nav-list').click()
  await expect(page.getByTestId('entity-list-section')).toBeVisible()

  // The created item is listed with its label
  const row = page
    .locator('[data-testid="entity-list-row"]', { hasText: entityId })
    .first()
  await expect(row).toBeVisible({ timeout: 15000 })
  await expect(row.getByTestId('entity-list-link')).toHaveText(entityId)
  await expect(row.getByTestId('entity-list-label')).toHaveText(label)
})

test('entity list type filter switches to properties', async ({
  page,
  request,
}) => {
  const propertyId = await createPropertyViaApi(request)

  await page.goto('/list?type=property&page=1')
  await expect(page.getByTestId('entity-list-section')).toBeVisible()

  const row = page
    .locator('[data-testid="entity-list-row"]', { hasText: propertyId })
    .first()
  await expect(row).toBeVisible({ timeout: 15000 })
  await expect(row.getByTestId('entity-list-link')).toHaveText(propertyId)
})

test('entity list pagination is disabled back on the first page', async ({
  page,
}) => {
  await page.goto('/list?type=item&page=1')
  await expect(page.getByTestId('entity-list-section')).toBeVisible()
  await expect(page.getByTestId('entity-list-prev')).toBeDisabled()
  await expect(page.getByTestId('entity-list-page')).toHaveText('Page 1')
})
