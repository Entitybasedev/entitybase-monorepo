import { test, expect } from '@playwright/test'
import { USER_ID, API_URL } from './helpers.js'

const COMPOSE = 'docker compose -f entitybase-backend/docker-compose.ci.yml'

async function produceEntityChange(entityId, revisionId) {
  const payload = JSON.stringify({
    id: entityId,
    rev: revisionId,
    type: 'edit',
    from_rev: 0,
    at: new Date().toISOString(),
    summary: 'e2e stream test',
    user: '90001',
  })
  if (process.env.E2E_MOCK === '1') {
    // Local mock: append straight to the mock api's event log
    await fetch(`${API_URL}/__mock/produce`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: payload,
    })
    return
  }
  const { execSync } = await import('node:child_process')
  // rpk reads the record value from stdin; it requires a trailing newline
  execSync(`${COMPOSE} exec -T redpanda rpk topic produce entity_change`, {
    cwd: '..',
    input: payload + '\n',
  })
}

test('change stream tab shows topics, connection status and events', async ({
  page,
}) => {
  await page.goto('/?tab=stream')

  // Topics load and the default topic is auto-selected
  const topicSelect = page.getByTestId('stream-topic-select')
  await expect(topicSelect).toBeVisible()
  await expect(topicSelect).toHaveValue('entity_change', { timeout: 15000 })

  // Health + connection status render
  const status = page.getByTestId('stream-status')
  await expect(status).toContainText('ok', { timeout: 15000 })
  await expect(status).toContainText('connected', { timeout: 15000 })

  // Produce a change event straight to the topic and expect it in the feed
  const entityId = `Q${Math.floor(100000 + Math.random() * 899999)}`
  await produceEntityChange(entityId, 1)

  const feed = page.getByTestId('stream-feed')
  await expect(feed).toContainText(entityId, { timeout: 15000 })
})

test('stream tab is reachable from the entities view via the menu', async ({
  page,
}) => {
  await page.goto('/')
  await expect(page.getByTestId('nav-entities')).toBeVisible()

  await page.getByTestId('nav-stream').click()

  await expect(page.getByTestId('stream-view')).toBeVisible()
  expect(new URL(page.url()).searchParams.get('tab')).toBe('stream')
})

test('creating an item produces a change event with the same QID', async ({
  page,
}) => {
  const label = `E2E Stream Item ${Date.now()}`

  // Create an item through the UI
  await page.goto('/')
  await page.getByTestId('item-label-input').fill(label)
  await page.getByTestId('user-id-input').fill(USER_ID)
  await page.getByTestId('create-item-button').click()

  const itemSection = page.getByTestId('item-section')
  await expect(itemSection).toBeVisible()
  const permalink = await page.getByTestId('item-permalink').getAttribute('href')
  const itemId = permalink.split('entity=')[1]
  expect(itemId).toMatch(/^Q\d+$/)

  // Switch to the change stream and expect the item's creation event.
  // The consumer subscribes at the latest offset, so replay from the
  // earliest offset to see the event published before connecting.
  await page.getByTestId('nav-stream').click()
  const topicSelect = page.getByTestId('stream-topic-select')
  await expect(topicSelect).toHaveValue('entity_change', { timeout: 15000 })

  await page.getByTestId('stream-offset-input').fill('0')
  await page.getByTestId('stream-reconnect').click()

  const feed = page.getByTestId('stream-feed')
  await expect(feed).toContainText(itemId, { timeout: 15000 })
})
