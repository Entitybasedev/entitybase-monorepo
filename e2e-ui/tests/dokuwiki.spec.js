import { test, expect } from '@playwright/test'
import {
  API_URL,
  DOKUWIKI_URL,
  USER_ID,
  createPropertyViaApi,
} from './helpers.js'

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

/**
 * Create a lexeme with one lemma, and return it with the item that plays its
 * language.
 *
 * A lexeme's language is a QID pointing at another entity, and the wiki shows
 * that entity's label, so the test needs an item it can read a label off. The
 * demo seed creates no language items, and POST /v1/entities/items ignores the
 * request body, so the id cannot be chosen: Q1860 cannot be created here. Make
 * an item instead and point the lexeme at whatever id it got.
 *
 * Note the response shape: this endpoint answers EntityResponse, whose id is
 * top level. Items and properties answer OperationResult[EntityIdResult], whose
 * id is nested under data, which is why the helpers above read them differently.
 */
async function createLexemeWithLemma(request, lemma) {
  const languageId = await createItemWithLabel(request, 'English')

  const created = await request.post(`${API_URL}/v1/entities/lexemes`, {
    headers: EDIT_HEADERS,
    data: {
      type: 'lexeme',
      language: languageId,
      lexical_category: 'Q1084',
      lemmas: { en: { language: 'en', value: lemma } },
    },
  })
  expect(created.ok()).toBeTruthy()
  const body = await created.json()
  const lexemeId = body.id
  expect(lexemeId).toMatch(/^L\d+$/)
  return { lexemeId, languageId }
}

/** Save a wiki page with the given content and wait for the rendered page. */
async function writeWikiPage(page, pageId, wikitext) {
  await page.goto(`${DOKUWIKI_URL}/doku.php?id=${pageId}&do=edit`)
  await page.locator('#wiki__text').fill(wikitext)
  await page.locator('#edbtn__save').click()
  // DokuWiki redirects to the page's pretty URL, not back to doku.php?id=
  await expect(page).toHaveURL(new RegExp(`/${pageId}$`))
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

test('an item without a label shows its id, marked as missing', async ({
  page,
  request,
}) => {
  // An id far beyond anything the instance will have allocated, so the item
  // really is absent and no label lookup can succeed for it
  const entityId = 'Q99999999'

  const pageId = `e2e-entity-missing-${Date.now()}`
  await writeWikiPage(page, pageId, `An item without a label: {{entity>${entityId}}}\n`)

  // The page still reads sensibly: the id stands in for the label that is not
  // there, marked so the problem is visible instead of silent
  const rendered = page.locator('#dokuwiki__content .entitybase-item').first()
  await expect(rendered).toHaveText(entityId)
  await expect(rendered).toHaveClass(/entitybase-missing/)
  await expect(rendered).toHaveAttribute('href', /\/entity\//)
})

test('a lexeme shows its lemma and language', async ({ page, request }) => {
  const lemma = `e2ewikiphrase${Date.now()}`
  const { lexemeId, languageId } = await createLexemeWithLemma(request, lemma)

  const pageId = `e2e-lexeme-macro-${Date.now()}`
  await writeWikiPage(page, pageId, `A lexeme from Entitybase: {{lexeme>${lexemeId}}}\n`)

  // A lexeme has no label; its lemma is the word, linked to the lexeme
  const rendered = page.locator('#dokuwiki__content .entitybase-lexeme').first()
  await expect(rendered).toHaveText(lemma)
  await expect(rendered).toHaveAttribute('href', new RegExp(`/entity/${lexemeId}$`))

  // The language is another entity, so it is shown as that entity's label
  const language = page.locator('#dokuwiki__content .entitybase-language').first()
  await expect(language).toHaveText('(English)')
  await expect(language.locator('a')).toHaveAttribute(
    'href',
    new RegExp(`/entity/${languageId}$`)
  )
})

test('a property shows its label and datatype', async ({ page, request }) => {
  const label = `e2ewikiproperty${Date.now()}`
  const propertyId = await createPropertyViaApi(request, label)

  const pageId = `e2e-property-macro-${Date.now()}`
  await writeWikiPage(page, pageId, `A property from Entitybase: {{property>${propertyId}}}\n`)

  const rendered = page.locator('#dokuwiki__content .entitybase-property').first()
  await expect(rendered).toHaveText(label)
  await expect(rendered).toHaveAttribute('href', new RegExp(`/entity/${propertyId}$`))

  // The datatype says what kind of value the property takes, which the label
  // does not: wikibase-item is shown as the 'item' the wiki calls it
  const datatype = page.locator('#dokuwiki__content .entitybase-datatype').first()
  await expect(datatype).toHaveText('(item)')
  await expect(datatype).toHaveAttribute('title', 'wikibase-item')
})