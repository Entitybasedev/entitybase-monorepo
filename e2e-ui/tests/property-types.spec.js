import { test, expect } from '@playwright/test'
import { registerViaUi } from './helpers.js'

// One test per property type, each walking create -> read -> edit.
//
// The list is data, so adding a property type means adding an entry here (plus
// its value input in the frontend property_types directory) rather than
// another copy of the same test.
const PROPERTY_TYPES = [
  {
    id: 'wikibase-item',
    label: 'Item',
    // An item-valued property points at another entity, and the UI shows that
    // entity's label once it resolves one
    placeholder: 'Q5',
    // A value the type must refuse
    invalidValue: 'not an id',
    newValue: (label) => ({ input: null, label }),
  },
  {
    id: 'string',
    label: 'String',
    // A string-valued property stores the text itself
    placeholder: 'a short text',
    invalidValue: null,
    newValue: (text) => ({ input: text, label: text }),
  },
]

async function createPropertyViaUi(page, type, label) {
  await page.goto('/create-property')
  await page.getByTestId('property-type-select').selectOption(type.id)
  await page.getByTestId('property-label-input').fill(label)
  await page.getByTestId('create-property-button').click()
  await expect(page.getByTestId('item-section')).toBeVisible()
  const href = await page.getByTestId('item-permalink').getAttribute('href')
  return href.split('/entity/')[1]
}

/** Create an item and return its id and label, for item-valued properties. */
async function createItem(page, label) {
  await page.goto('/create-item')
  await page.getByTestId('item-label-input').fill(label)
  await page.getByTestId('create-item-button').click()
  await expect(page.getByTestId('item-section')).toBeVisible()
  const href = await page.getByTestId('item-permalink').getAttribute('href')
  return { id: href.split('/entity/')[1], label }
}

for (const type of PROPERTY_TYPES) {
  test(`property type ${type.id}: create, read and edit`, async ({ page }) => {
    await registerViaUi(page)
    const stamp = Date.now()

    // Create: the type picker offers this type, and the property keeps it
    const propertyId = await createPropertyViaUi(
      page,
      type,
      `E2E ${type.label} ${stamp}`
    )
    expect(propertyId).toMatch(/^P\d+$/)

    // Read: the property page shows the type it was created with
    await expect(page.getByTestId('property-datatype')).toHaveText(type.label)

    const subject = await createItem(page, `E2E subject ${stamp}`)
    await page.goto(`/entity/${propertyId}`)

    // Read: the statement form uses this type's value input
    await page.getByTestId('statement-property-input').fill(propertyId)
    await expect(page.getByTestId('statement-value-input')).toHaveAttribute(
      'placeholder',
      type.placeholder
    )

    if (type.invalidValue) {
      // This type only accepts entity ids, and says so
      await page.getByTestId('statement-value-input').fill(type.invalidValue)
      await expect(page.getByTestId('statement-value-input-error')).toBeVisible()
      await page.getByTestId('statement-value-input').fill('')
    }

    // Create a statement whose value suits the type
    const first = type.newValue(subject.label)
    const firstInput = first.input ?? subject.id
    await page.getByTestId('statement-value-input').fill(firstInput)
    await page.getByTestId('add-statement-button').click()
    await expect(page.getByTestId('statement').first()).toBeVisible()
    await expect(page.getByTestId('statement-value').first()).toHaveText(first.label)

    // Edit: change the value and read it back
    const second = type.newValue(`${type.label} edited ${stamp}`)
    // An entity-valued change needs a second entity, and creating one lands on
    // that entity's page, so go back to the property whose statement we edit
    let secondInput = second.input
    if (!secondInput) {
      secondInput = (await createItem(page, second.label)).id
      await page.goto(`/entity/${propertyId}`)
      await expect(page.getByTestId('statement').first()).toBeVisible()
    }
    await page.getByTestId('statement-edit-button').first().click()
    await page.getByTestId('statement-edit-input').fill(secondInput)
    await page.getByTestId('statement-save-button').click()
    await expect(page.getByTestId('statement-edit-input')).toHaveCount(0)
    await expect(page.getByTestId('statement-value').first()).toHaveText(second.label)

    // The type and the value survive a reload
    await page.reload()
    await expect(page.getByTestId('property-datatype')).toHaveText(type.label)
    await expect(page.getByTestId('statement-value').first()).toHaveText(second.label)
  })
}

test('the type picker offers exactly the API property types', async ({ page }) => {
  await registerViaUi(page)

  await page.goto('/create-property')
  const select = page.getByTestId('property-type-select')
  // The API's first type is preselected, so there is always a type to use
  await expect(select).toHaveValue('wikibase-item')
  expect(await select.locator('option').allTextContents()).toEqual(['Item', 'String'])
})