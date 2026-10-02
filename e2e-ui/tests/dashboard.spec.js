import { test, expect } from '@playwright/test'
import { createPropertyViaApi, registerViaUi } from './helpers.js'

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
  const propertyId = await createPropertyViaApi(request, 'instance of')
  await registerViaUi(page)

  await page.goto('/create-item')
  await page.getByTestId('item-label-input').fill(`E2E Statements ${Date.now()}`)
  await page.getByTestId('create-item-button').click()
  await expect(page.getByTestId('item-section')).toBeVisible()

  for (const value of ['Q5', 'Q1']) {
    await page.getByTestId('statement-property-input').fill(propertyId)
    await page.getByTestId('statement-value-input').fill(value)
    await page.getByTestId('add-statement-button').click()
    await expect(page.getByTestId('statement')).toHaveCount(
      value === 'Q5' ? 1 : 2
    )
  }

  const group = page.getByTestId('statement-group').first()
  await expect(group).toHaveAttribute('id', propertyId)
  await expect(group.getByTestId('statement-group-count')).toHaveText('2')
  await expect(group.getByTestId('statement')).toHaveCount(2)

  // The group is linkable by fragment
  const groupId = await group.getAttribute('id')
  await page.goto(`${new URL(page.url()).pathname}#${groupId}`)
  await expect(page.getByTestId('statement-group').first()).toHaveAttribute(
    'id',
    groupId
  )
})