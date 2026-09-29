import { test, expect } from '@playwright/test'

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
  const { execSync } = await import('node:child_process')
  // rpk reads the record value from stdin
  execSync(`${COMPOSE} exec -T redpanda rpk topic produce entity_change`, {
    cwd: '..',
    input: payload,
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
