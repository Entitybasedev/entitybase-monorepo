import { test, expect } from '@playwright/test'

const USER_ID = process.env.E2E_USER_ID || '90001'

test('create a property via the UI', async ({ page }) => {
  const label = `E2E Property ${Date.now()}`

  await page.goto('/')

  await page.getByTestId('property-label-input').fill(label)
  await page.getByTestId('create-property-button').click()

  const itemSection = page.getByTestId('item-section')
  await expect(itemSection).toBeVisible()
  await expect(page.getByTestId('item-label')).toHaveText(label)

  // Property IDs are P-prefixed and persisted server-side
  const permalink = await page.getByTestId('item-permalink').getAttribute('href')
  expect(permalink).toMatch(/\?entity=P\d+$/)

  await page.reload()
  await expect(page.getByTestId('item-label')).toHaveText(label)
})

test('create a lexeme via the UI', async ({ page }) => {
  const lemma = `e2elexeme${Date.now()}`

  await page.goto('/')

  await page.getByTestId('lemma-input').fill(lemma)
  await page.getByTestId('lexeme-language-input').fill('Q1860')
  await page.getByTestId('lexeme-category-input').fill('Q1084')
  await page.getByTestId('create-lexeme-button').click()

  const itemSection = page.getByTestId('item-section')
  await expect(itemSection).toBeVisible()

  // Lexeme IDs are L-prefixed and persisted server-side
  const permalink = await page.getByTestId('item-permalink').getAttribute('href')
  expect(permalink).toMatch(/\?entity=L\d+$/)

  await page.reload()
  await expect(itemSection).toBeVisible()
})

const API_URL = process.env.API_URL || 'http://localhost:8083'

test('create a lexeme and add a statement via the UI', async ({ page, request }) => {
  // The statement add validates property existence, so create one first.
  const propRes = await request.post(`${API_URL}/v1/entities/properties`, {
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': USER_ID,
      'X-Edit-Summary': 'e2e setup property',
    },
    data: {
      type: 'property',
      datatype: 'wikibase-item',
      labels: { en: { language: 'en', value: 'instance of' } },
    },
  })
  expect(propRes.ok()).toBeTruthy()
  const propBody = await propRes.json()
  const propertyId = propBody.data?.entity_id ?? propBody.entity_id
  expect(propertyId).toMatch(/^P\d+$/)

  // Create the lexeme through the UI
  const lemma = `e2elexeme${Date.now()}`
  await page.goto('/')
  await page.getByTestId('lemma-input').fill(lemma)
  await page.getByTestId('lexeme-language-input').fill('Q1860')
  await page.getByTestId('lexeme-category-input').fill('Q1084')
  await page.getByTestId('create-lexeme-button').click()

  const itemSection = page.getByTestId('item-section')
  await expect(itemSection).toBeVisible()
  const permalink = await page.getByTestId('item-permalink').getAttribute('href')
  const lexemeId = permalink.split('entity=')[1]
  expect(lexemeId).toMatch(/^L\d+$/)

  // Add a statement to the lexeme through the UI
  await page.getByTestId('statement-property-input').fill(propertyId)
  await page.getByTestId('statement-value-input').fill('Q5')
  await page.getByTestId('add-statement-button').click()

  const statement = page.getByTestId('statement').first()
  await expect(statement).toBeVisible()
  await expect(statement.getByTestId('statement-value')).toHaveText('Q5')

  // Reload to prove it persisted server-side
  await page.reload()
  await expect(itemSection).toBeVisible()
  await expect(page.getByTestId('statement')).toHaveCount(1)
  await expect(page.getByTestId('statement').first().getByTestId('statement-value')).toHaveText('Q5')
})
