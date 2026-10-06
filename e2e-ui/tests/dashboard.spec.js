import { test, expect } from '@playwright/test'
import {
  createItemViaApi,
  createPropertyViaApi,
  registerViaUi,
} from './helpers.js'

test('dashboard is the landing page and links to detailed statistics', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByTestId('dashboard-section')).toBeVisible()
  await expect(page.getByTestId('dashboard-edits-7d')).not.toHaveText('—')
  await expect(page.getByTestId('dashboard-edits-30d')).not.toHaveText('—')
  await expect(page.getByTestId('dashboard-items')).not.toHaveText('—')
  await expect(page.getByTestId('dashboard-properties')).not.toHaveText('—')

  await page.getByTestId('dashboard-statistics-link').click()
  await expect(page.getByTestId('statistics-section')).toBeVisible()
  expect(new URL(page.url()).pathname).toBe('/statistics')
  await expect(page.getByTestId('statistics-general')).toBeVisible()
  await expect(page.getByTestId('statistics-deduplication')).toBeVisible()
})

test('statistics page is reachable from the top menu', async ({ page }) => {
  await page.goto('/')

  await page.getByTestId('nav-statistics').click()

  await expect(page.getByTestId('statistics-section')).toBeVisible()
  expect(new URL(page.url()).pathname).toBe('/statistics')
})

test('statements on an entity are grouped by property with anchors', async ({
  page,
  request,
}) => {
  const firstProperty = await createPropertyViaApi(request, 'instance of')
  const secondProperty = await createPropertyViaApi(request, 'country')
  // A statement's value has to be an entity that exists, so the values here
  // are real items rather than ids written down in the test
  const firstValue = await createItemViaApi(request, 'first value')
  const secondValue = await createItemViaApi(request, 'second value')
  await registerViaUi(page)

  await page.goto('/create-item')
  await page.getByTestId('item-label-input').fill(`E2E Statements ${Date.now()}`)
  await page.getByTestId('create-item-button').click()
  await expect(page.getByTestId('item-section')).toBeVisible()

  for (const [propertyId, value] of [
    [firstProperty, firstValue],
    [secondProperty, secondValue],
  ]) {
    await page.getByTestId('statement-property-input').fill(propertyId)
    await page.getByTestId('statement-value-input').fill(value)
    await page.getByTestId('add-statement-button').click()
    // Saving reloads the entity, which briefly empties the statement list;
    // wait for the button to go idle again so the reload has finished
    await expect(page.getByTestId('add-statement-button')).toHaveText('Add statement', {
      timeout: 30_000,
    })
  }

  // One anchored group per property, each with its own value
  const groups = page.getByTestId('statement-group')
  await expect(groups).toHaveCount(2)
  await expect(page.getByTestId('statement')).toHaveCount(2)
  await expect(page.getByTestId('statement-group-count')).toHaveText(['1', '1'])

  const ids = await groups.evaluateAll((nodes) => nodes.map((n) => n.id))
  expect(ids).toEqual([firstProperty, secondProperty])

  // Each group is linkable by fragment
  await page.goto(`${new URL(page.url()).pathname}#${secondProperty}`)
  await expect(page.getByTestId('statement-group').last()).toHaveAttribute(
    'id',
    secondProperty
  )
})

test('a statement value can be edited and removed in the UI', async ({
  page,
  request,
}) => {
  const propertyId = await createPropertyViaApi(request, 'instance of')
  const firstValue = await createItemViaApi(request, 'edit first value')
  const secondValue = await createItemViaApi(request, 'edit second value')
  await registerViaUi(page)

  await page.goto('/create-item')
  await page.getByTestId('item-label-input').fill(`E2E EditStatement ${Date.now()}`)
  await page.getByTestId('create-item-button').click()
  await expect(page.getByTestId('item-section')).toBeVisible()

  await page.getByTestId('statement-property-input').fill(propertyId)
  await page.getByTestId('statement-value-input').fill(firstValue)
  await page.getByTestId('add-statement-button').click()
  await expect(page.getByTestId('add-statement-button')).toHaveText('Add statement')
  await expect(page.getByTestId('statement')).toHaveCount(1)

  // Editing prefills the current value and saves on click
  await page.getByTestId('statement-edit-button').click()
  await expect(page.getByTestId('statement-edit-input')).toHaveValue(firstValue)
  await page.getByTestId('statement-edit-input').fill(secondValue)
  await page.getByTestId('statement-save-button').click()
  await expect(page.getByTestId('statement-edit-input')).toHaveCount(0)
  await expect(page.getByTestId('statement')).toHaveCount(1)
  await expect(page.getByTestId('error-banner')).toHaveCount(0)

  // Cancel leaves the statement as it was
  await page.getByTestId('statement-edit-button').click()
  await page.getByTestId('statement-edit-input').fill('Q146')
  await page.getByTestId('statement-cancel-button').click()
  await expect(page.getByTestId('statement-edit-input')).toHaveCount(0)
  await expect(page.getByTestId('statement')).toHaveCount(1)

  // Remove empties the property group
  await page.getByTestId('statement-remove-button').click()
  await expect(page.getByTestId('statement')).toHaveCount(0)
  await expect(page.getByTestId('no-statements')).toBeVisible()
  await expect(page.getByTestId('error-banner')).toHaveCount(0)
})