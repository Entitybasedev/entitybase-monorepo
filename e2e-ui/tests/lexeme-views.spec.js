import { test, expect } from '@playwright/test'
import { registerViaUi } from './helpers.js'

test('a lexeme shows lemmas, senses and forms instead of labels', async ({
  page,
  request,
}) => {
  const apiUrl = process.env.API_URL || 'http://localhost:8083'
  const lemma = `e2elexeme${Date.now()}`

  await registerViaUi(page)

  await page.goto('/create-lexeme')
  await page.getByTestId('lemma-input').fill(lemma)
  await page.getByTestId('lexeme-language-input').fill('Q1860')
  await page.getByTestId('lexeme-category-input').fill('Q1084')
  await page.getByTestId('create-lexeme-button').click()

  await expect(page.getByTestId('item-section')).toBeVisible()
  await expect(page.getByTestId('item-type-badge')).toHaveText('Lexeme')

  // Lemmas, not labels
  await expect(page.getByTestId('lexeme-lemma')).toHaveText(lemma)
  await expect(page.getByTestId('item-label')).toHaveCount(0)
  await expect(page.getByTestId('edit-aliases-button')).toHaveCount(0)

  // Language and lexical category are shown
  await expect(page.getByTestId('lexeme-language')).not.toBeEmpty()
  await expect(page.getByTestId('lexeme-category')).not.toBeEmpty()

  // Add a sense and a form through the API, then reload the page
  const lexemeId = await page.getByTestId('item-permalink').getAttribute('href')
  const id = lexemeId.split('/entity/')[1]
  const headers = { 'Content-Type': 'application/json', 'X-User-ID': '0' }
  await request.post(`${apiUrl}/v1/entities/lexemes/${id}/senses`, {
    headers: { ...headers, 'X-Edit-Summary': 'e2e sense' },
    data: { glosses: { en: { language: 'en', value: 'a gloss from e2e' } } },
  })
  await request.post(`${apiUrl}/v1/entities/lexemes/${id}/forms`, {
    headers: { ...headers, 'X-Edit-Summary': 'e2e form' },
    data: { representations: { en: { language: 'en', value: 'a representation' } } },
  })

  await page.reload()
  await expect(page.getByTestId('lexeme-sense')).toHaveCount(1)
  await expect(page.getByTestId('lexeme-gloss')).toHaveText('a gloss from e2e')
  await expect(page.getByTestId('lexeme-form')).toHaveCount(1)
  await expect(page.getByTestId('lexeme-representation')).toHaveText('a representation')
})

test('a property shows its label and statements but no aliases', async ({ page }) => {
  await registerViaUi(page)

  await page.goto('/create-property')
  const label = `E2E Property ${Date.now()}`
  await page.getByTestId('property-label-input').fill(label)
  await page.getByTestId('create-property-button').click()

  await expect(page.getByTestId('item-section')).toBeVisible()
  await expect(page.getByTestId('item-type-badge')).toHaveText('Property')
  await expect(page.getByTestId('item-label')).toHaveText(label)
  await expect(page.getByTestId('edit-aliases-button')).toHaveCount(0)
  await expect(page.getByTestId('statement-form')).toBeVisible()
})