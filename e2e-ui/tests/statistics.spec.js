import { test, expect } from '@playwright/test'
import { registerViaUi } from './helpers.js'

/**
 * One row of the deduplication table, addressed by its type name.
 * Types are statements, qualifiers, references, snaks, sitelinks and terms,
 * so an exact match keeps "terms" from picking up another row.
 */
function dedupRow(page, type) {
  return page
    .locator('[data-testid="statistics-deduplication"] tbody tr')
    .filter({
      has: page
        .getByTestId('statistics-deduplication-type')
        .filter({ hasText: new RegExp(`^${type}$`) }),
    })
}

/** Read one deduplication row as numbers. */
async function dedupRowNumbers(page, type) {
  const row = dedupRow(page, type)
  await expect(row).toBeVisible()
  const factor = await row
    .getByTestId('statistics-deduplication-factor')
    .innerText()
  return {
    unique: Number(
      await row.getByTestId('statistics-deduplication-unique').innerText()
    ),
    refs: Number(
      await row.getByTestId('statistics-deduplication-refs').innerText()
    ),
    factor: Number(factor.replace('%', '')),
    saved: Number(
      await row.getByTestId('statistics-deduplication-saved').innerText()
    ),
  }
}

test('a term used twice is reported as deduplicated', async ({ page }) => {
  await registerViaUi(page)
  // The same text as both a label and a description: stored once, referenced
  // twice, so the term ledger has a row with ref_count 2
  const term = `e2ededup${Date.now()}`

  await page.goto('/create-item')
  await page.getByTestId('item-label-input').fill(term)
  await page.getByTestId('create-item-button').click()
  await expect(page.getByTestId('item-section')).toBeVisible()

  await page.getByTestId('edit-description-button').click()
  await page.getByTestId('description-edit-input').fill(term)
  await page.getByTestId('save-description-button').click()
  await expect(page.getByTestId('item-description')).toHaveText(term)

  await page.goto('/statistics')
  await expect(page.getByTestId('statistics-deduplication')).toBeVisible()

  const terms = await dedupRowNumbers(page, 'terms')

  // Terms used to report zero unique hashes and zero references
  expect(terms.unique).toBeGreaterThan(0)
  expect(terms.refs).toBeGreaterThan(0)
  // Our term is referenced twice under one hash, so something was deduplicated
  expect(terms.saved).toBeGreaterThan(0)
  expect(terms.unique).toBeLessThanOrEqual(terms.refs)
})

test('every deduplication row is internally consistent', async ({ page }) => {
  await registerViaUi(page)
  await page.goto('/statistics')

  const table = page.getByTestId('statistics-deduplication')
  await expect(table).toBeVisible()

  const types = await table
    .getByTestId('statistics-deduplication-type')
    .allInnerTexts()
  expect(types.length).toBeGreaterThan(0)

  for (const type of types) {
    const { unique, refs, factor, saved } = await dedupRowNumbers(page, type)
    // Duplicates saved is the references beyond the first
    expect(saved, `${type}: saved`).toBe(refs - unique)
    if (refs > 0) {
      // Dedup factor is the share of references that were duplicates
      expect(factor, `${type}: factor`).toBeCloseTo(
        ((refs - unique) / refs) * 100,
        1
      )
    }
  }
})