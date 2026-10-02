import { test, expect } from '@playwright/test'
import { registerViaUi } from './helpers.js'

test('all-terms page lists label, description and aliases per language', async ({ page }) => {
  const label = `E2E Terms ${Date.now()}`
  await registerViaUi(page)

  await page.goto('/create-item')
  await page.getByTestId('item-label-input').fill(label)
  await page.getByTestId('create-item-button').click()
  await expect(page.getByTestId('item-section')).toBeVisible()

  // Add an English description
  await page.getByTestId('edit-description-button').click()
  await page.getByTestId('description-edit-input').fill('terms e2e description')
  await page.getByTestId('save-description-button').click()
  await expect(page.getByTestId('item-description')).toHaveText('terms e2e description')

  // Add English aliases
  await page.getByTestId('edit-aliases-button').click()
  await page.getByTestId('aliases-edit-input').fill('DNA')
  await page.getByTestId('aliases-edit-input').press('Enter')
  await page.getByTestId('save-aliases-button').click()
  await expect(page.getByTestId('item-alias')).toHaveText('DNA')

  // All-terms page shows the terms for the chain languages
  await page.getByTestId('item-terms-link').click()
  await expect(page.getByTestId('terms-section')).toBeVisible()
  await expect(page.getByTestId('terms-row')).toHaveCount(1)
  await expect(page.getByTestId('terms-lang')).toHaveText('en')
  await expect(page.getByTestId('terms-label')).toHaveText(label)
  await expect(page.getByTestId('terms-description')).toHaveText('terms e2e description')
  await expect(page.getByTestId('terms-alias')).toHaveText('DNA')
  await expect(page.getByTestId('terms-count')).toHaveText(/Showing 1 of \d+ languages/)

  // Back to the entity page
  await page.getByTestId('back-to-entity-link').click()
  await expect(page.getByTestId('item-section')).toBeVisible()
})
