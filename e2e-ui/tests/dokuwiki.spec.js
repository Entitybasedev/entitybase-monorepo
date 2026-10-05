import { test, expect } from '@playwright/test'
import { API_URL, DOKUWIKI_URL, USER_ID } from './helpers.js'

// The wiki only runs in the docker stack; the mock setup has no DokuWiki.
test.skip(process.env.E2E_MOCK === '1', 'the wiki is not part of the mock setup')

const EDIT_HEADERS = {
  'Content-Type': 'application/json',
  'X-User-ID': USER_ID,
  'X-Edit-Summary': 'e2e dokuwiki setup',
}

/**
 * Create an item and label it. The create endpoint makes an *empty* item, so
 * the label is a second request; the plugin looks labels up on the API
 * directly, which is why no indexing wait is needed here.
 */
async function createItemWithLabel(request, label) {
  const created = await request.post(`${API_URL}/v1/entities/items`, {
    headers: EDIT_HEADERS,
  })
  expect(created.ok()).toBeTruthy()
  const body = await created.json()
  const entityId = body.data?.entity_id ?? body.entity_id
  expect(entityId).toMatch(/^Q\d+$/)

  const labelled = await request.put(`${API_URL}/v1/entities/${entityId}/labels/en`, {
    headers: EDIT_HEADERS,
    data: { language: 'en', value: label },
  })
  expect(labelled.ok()).toBeTruthy()
  return entityId
}

/** Save a wiki page with the given content and wait for the rendered page. */
async function writeWikiPage(page, pageId, wikitext) {
  await page.goto(`${DOKUWIKI_URL}/doku.php?id=${pageId}&do=edit`)
  await page.locator('#wiki__text').fill(wikitext)
  await page.locator('#edbtn__save').click()
  await expect(page).toHaveURL(new RegExp(`id=${pageId}(&|$)`))
}

test('a wiki article with the entity macro shows the label of the item', async ({
  page,
  request,
}) => {
  const label = `E2E Wiki Item ${Date.now()}`
  const entityId = await createItemWithLabel(request, label)

  // A fresh page id per run, so a rerun never edits a leftover page
  const pageId = `e2e-entity-macro-${Date.now()}`
  await writeWikiPage(page, pageId, `An item from Entitybase: {{entity>${entityId}}}\n`)

  // The macro renders as a link to the item, showing its label
  const rendered = page.locator('#dokuwiki__content .entitybase-item').first()
  await expect(rendered).toHaveText(label)
  await expect(rendered).toHaveAttribute('href', /\/entity\//)
  await expect(rendered).toHaveAttribute('title', entityId)
  // A label was found, so the item is not marked as missing one
  await expect(rendered).not.toHaveClass(/entitybase-missing/)
})