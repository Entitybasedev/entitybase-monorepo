import { expect } from '@playwright/test'

export const USER_ID = process.env.E2E_USER_ID || '90001'
export const API_URL = process.env.API_URL || 'http://localhost:8083'

/**
 * Create a property via the API. Statement adds validate that the
 * property entity exists, so tests that add statements must create
 * one first (property IDs are auto-enumerated, e.g. P30000).
 */
export async function createPropertyViaApi(request, label = 'instance of') {
  const res = await request.post(`${API_URL}/v1/entities/properties`, {
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': USER_ID,
      'X-Edit-Summary': 'e2e setup property',
    },
    data: {
      type: 'property',
      datatype: 'wikibase-item',
      labels: { en: { language: 'en', value: label } },
    },
  })
  expect(res.ok()).toBeTruthy()
  const body = await res.json()
  const propertyId = body.data?.entity_id ?? body.entity_id
  expect(propertyId).toMatch(/^P\d+$/)
  return propertyId
}

