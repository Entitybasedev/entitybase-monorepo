import { test, expect } from '@playwright/test'
import { registerViaUi } from './helpers.js'

test('aliases can be added and removed via the edit box', async ({ page }) => {
  const label = `E2E Aliases ${Date.now()}`

  await registerViaUi(page)
  await page.goto('/create-item')
  await page.getByTestId('item-label-input').fill(label)
  await page.getByTestId('create-item-button').click()
  await expect(page.getByTestId('item-section')).toBeVisible()

  // No aliases yet
  await expect(page.getByTestId('item-aliases')).toHaveCount(0)

  // Add aliases via the edit box
  await page.getByTestId('edit-aliases-button').click()
  await page
    .getByTestId('aliases-edit-input')
    .fill(`alpha one, beta two, alpha one`)
  await page.getByTestId('save-aliases-button').click()

  const chips = page.getByTestId('item-alias')
  await expect(chips).toHaveCount(2, { timeout: 15000 })
  await expect(chips.first()).toHaveText('alpha one')
  await expect(chips.nth(1)).toHaveText('beta two')

  // Remove one and save
  await page.getByTestId('edit-aliases-button').click()
  await page.getByTestId('aliases-edit-input').fill('beta two')
  await page.getByTestId('save-aliases-button').click()

  await expect(page.getByTestId('item-alias')).toHaveCount(1, { timeout: 15000 })
  await expect(page.getByTestId('item-alias')).toHaveText('beta two')
})
