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
  expect(permalink).toMatch(/\/entity\/L\d+$/)
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
  const lexemeId = permalink.split('/entity/')[1]
  expect(lexemeId).toMatch(/^L\d+$/)

  // Add a statement to the lexeme through the UI
  await page.getByTestId('statement-property-input').fill(propertyId)
  await page.getByTestId('statement-value-input').fill('Q5')
  await page.getByTestId('add-statement-button').click()

  const statement = page.getByTestId('statement').first()
  await expect(statement).toBeVisible()
  // Statements are grouped under an anchored property header
  const group = page.getByTestId('statement-group').first()
  await expect(group).toHaveAttribute('id', propertyId)
  await expect(group.getByTestId('statement-property')).toHaveText(propertyId)
  await expect(statement.getByTestId('statement-value')).toHaveText('Q5')
  await expect(statement.getByTestId('statement-value')).toBeVisible()
})

test('add a sense and a form to a lexeme via the UI', async ({ page }) => {
  await registerViaUi(page)
  const lemma = `e2elexeme${Date.now()}`

  await page.goto('/create-lexeme')
  await page.getByTestId('lemma-input').fill(lemma)
  await page.getByTestId('lexeme-language-input').fill('Q1860')
  await page.getByTestId('lexeme-category-input').fill('Q1084')
  await page.getByTestId('create-lexeme-button').click()
  await expect(page.getByTestId('item-section')).toBeVisible()

  // A sense needs a gloss in some language
  await page.getByTestId('new-sense-button').click()
  await page.getByTestId('sense-gloss-lang-select').selectOption('en')
  await page.getByTestId('sense-gloss-input').fill(`${lemma} gloss`)
  await page.getByTestId('add-sense-button').click()

  const sense = page.getByTestId('lexeme-sense').first()
  await expect(sense.getByTestId('lexeme-gloss')).toHaveText(`${lemma} gloss`)

  // A form needs a value; grammatical features are optional chips
  await page.getByTestId('new-form-button').click()
  await page.getByTestId('form-representation-lang-select').selectOption('en')
  await page.getByTestId('form-representation-input').fill(`${lemma}s`)
  const feature = page.getByTestId('form-grammatical-feature-input')
  await feature.fill('Q110786')
  await feature.press('Enter')
  await expect(
    page.getByTestId('form-grammatical-feature-chip-Q110786')
  ).toBeVisible()
  await page.getByTestId('add-form-button').click()

  const form = page.getByTestId('lexeme-form').first()
  await expect(form.getByTestId('lexeme-representation')).toHaveText(`${lemma}s`)
  // The feature is stored; it is rendered as its label, or as the QID
  // when the label cannot be resolved
  const features = form.getByTestId('lexeme-grammatical-features')
  await expect(features).toBeVisible()
  await expect(features).toHaveText(/plural|Q110786/)
})
