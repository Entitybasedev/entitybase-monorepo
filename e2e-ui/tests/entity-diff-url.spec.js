import { test, expect } from '@playwright/test'
import {
  USER_ID,
  API_URL,
  createItemViaApi,
  createPropertyViaApi,
  registerViaUi,
} from './helpers.js'

test('diffs have unique shareable URLs', async ({ page, request }) => {
  await registerViaUi(page)

  const propertyId = await createPropertyViaApi(request)
  // The statement's value has to be an entity that exists, or the add is
  // rejected and the third revision this test counts never happens
  const valueId = await createItemViaApi(request, 'diff url target')
  const H = { 'Content-Type': 'application/json', 'X-User-ID': USER_ID, 'X-Edit-Summary': 'diff url e2e' }

  // Create an item, set a label, then add a statement -> 3 revisions
  const res = await request.post(`${API_URL}/v1/entities/items`, { headers: H, data: { type: 'item' } })
  expect(res.ok()).toBeTruthy()
  const entityId = (await res.json()).data?.entity_id

  await request.put(`${API_URL}/v1/entities/${entityId}/labels/en`, {
    headers: H,
    data: { language: 'en', value: `Diff URL ${Date.now()}` },
  })
  const added = await request.post(`${API_URL}/v1/entities/${entityId}/statements`, {
    headers: H,
    data: { claim: { id: `c${Date.now()}`, mainsnak: { snaktype: 'value', property: propertyId, datavalue: { value: { id: valueId }, type: 'wikibase-item' } }, type: 'statement', rank: 'normal' } },
  })
  expect(added.ok()).toBeTruthy()

  // Open history and diff the newest revision
  await page.goto(`/${entityId}/history`)
  await page.getByTestId('history-diff').first().click()

  // The diff has its own URL
  await expect(page.getByTestId('diff-view')).toBeVisible()
  const url = new URL(page.url())
  expect(url.pathname).toBe(`/${entityId}/history/3/2`)

  // The URL is shareable: opening it fresh computes the same diff
  await page.goto(url.pathname)
  await expect(page.getByTestId('diff-view')).toBeVisible({ timeout: 15000 })
  await expect(page.getByTestId('diff-added').first()).toContainText(propertyId)

  // Closing returns to the history list
  await page.getByTestId('diff-close').click()
  await expect(page).toHaveURL(new RegExp(`/${entityId}/history$`))
})
