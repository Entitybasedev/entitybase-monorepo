import { test, expect } from '@playwright/test'
import { createPropertyViaApi, registerViaUi } from './helpers.js'

test('create a lexeme via the UI', async ({ page }) => {
  await registerViaUi(page)
  const lemma = `e2elexeme${Date.now()}`

  await page.goto('/create-lexeme')

  await page.getByTestId('lemma-input').fill(lemma)
  await page.getByTestId('lexeme-language-input').fill('Q1860')
  await page.getByTestId('lexeme-category-input').fill('Q1084')
  await page.getByTestId('create-lexeme-button').click()

  const itemSection = page.getByTestId('item-section')
  await expect(itemSection).toBeVisible()

  // Lexeme IDs are L-prefixed and persisted server-side
  const permalink = await page.getByTestId('item-permalink').getAttribute('href')
  expect(permalink).toMatch(/\?entity=L\d+$/)
})

test('create a lexeme and add a statement via the UI', async ({ page, request }) => {
  await registerViaUi(page)
  // The statement add validates property existence, so create one first.
  const propertyId = await createPropertyViaApi(request)

  // Create the lexeme through the UI
  const lemma = `e2elexeme${Date.now()}`
  await page.goto('/create-lexeme')
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
  await expect(statement.getByTestId('statement-property')).toHaveText(propertyId)
  await expect(statement.getByTestId('statement-value')).toHaveText('Q5')
  await expect(statement.getByTestId('statement-value')).toBeVisible()
})
