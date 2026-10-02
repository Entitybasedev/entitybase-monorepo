import { test, expect } from '@playwright/test'
import { registerViaUi } from './helpers.js'

test('item view shows a type badge and supports label editing', async ({ page }) => {
  const label = `E2E EditLabel ${Date.now()}`
  await registerViaUi(page)

  await page.goto('/create-item')
  await page.getByTestId('item-label-input').fill(label)
  await page.getByTestId('create-item-button').click()
  await expect(page.getByTestId('item-section')).toBeVisible()

  await expect(page.getByTestId('item-type-badge')).toHaveText('Item')

  await page.getByTestId('edit-label-button').click()
  await page.getByTestId('label-edit-input').fill(label + ' v2')
  await page.getByTestId('save-label-button').click()

  await expect(page.getByTestId('item-label')).toHaveText(label + ' v2')
})
