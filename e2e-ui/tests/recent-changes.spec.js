import { test, expect } from '@playwright/test'
import { USER_ID } from './helpers.js'

test('recent changes is in the menu and lists the new entity', async ({
  page,
}) => {
  const label = `E2E Recent ${Date.now()}`

  // Create an item via the UI
  await page.goto('/')
  await page.getByTestId('item-label-input').fill(label)
  await page.getByTestId('user-id-input').fill(USER_ID)
  await page.getByTestId('create-item-button').click()

  const itemSection = page.getByTestId('item-section')
  await expect(itemSection).toBeVisible()
  const entityId = new URL(page.url()).searchParams.get('entity')
  expect(entityId).toMatch(/^Q\d+$/)

  // Find the page via the menu
  await page.getByTestId('nav-recent').click()
  await expect(page.getByTestId('recent-changes-section')).toBeVisible()

  // The created item is listed with a humanized change type
  const rows = page.locator('[data-testid="recent-row"]', { hasText: entityId })
  await expect(rows.first()).toBeVisible({ timeout: 15000 })
  await expect(rows.filter({ hasText: 'New entity' }).first()).toBeVisible()
})

test('recent changes rows link back to the entity', async ({ page }) => {
  const label = `E2E Recent Link ${Date.now()}`

  await page.goto('/')
  await page.getByTestId('item-label-input').fill(label)
  await page.getByTestId('user-id-input').fill(USER_ID)
  await page.getByTestId('create-item-button').click()
  await expect(page.getByTestId('item-section')).toBeVisible()
  const entityId = new URL(page.url()).searchParams.get('entity')

  await page.getByTestId('nav-recent').click()
  const row = page
    .locator('[data-testid="recent-row"]', { hasText: entityId })
    .first()
  await expect(row).toBeVisible({ timeout: 15000 })

  await row.getByTestId('recent-entity').click()
  await expect(page.getByTestId('item-section')).toBeVisible()
  expect(new URL(page.url()).searchParams.get('entity')).toBe(entityId)
})

test('hide imports filter is available', async ({ page }) => {
  await page.goto('/recent')
  await expect(page.getByTestId('recent-changes-section')).toBeVisible()

  const toggle = page.getByTestId('recent-hide-imports')
  await expect(toggle).toBeVisible()
  await toggle.check()
})
