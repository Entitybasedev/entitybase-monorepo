<template>
  <section class="panel stream-panel" data-testid="stream-view">
    <h2>Change stream</h2>

    <div v-if="error" class="error" data-testid="stream-error">{{ error }}</div>
    <div v-if="info" class="stream-info" data-testid="stream-info">{{ info }}</div>
    <div v-if="warning" class="stream-info" data-testid="stream-warning">{{ warning }}</div>

    <TopicControls
      v-model:selected-topic="selectedTopic"
      v-model:offset="offset"
      v-model:since="since"
      v-model:limit="limit"
      :topics="topics"
      @refresh="fetchTopics"
    />

    <StatusBar
      :health="health"
      :topic-connected="topicConnected"
      :is-connecting="isConnecting"
      :connection-duration="connectionDuration"
      :rate-current="rateCurrent"
      :rate-average="rateAverage"
    />

    <MessageFeed
      v-model:pretty-print="prettyPrint"
      v-model:is-paused="isPaused"
      :messages="formattedMessages"
      @copy="copyMessages"
      @clear="clearMessages"
      @reconnect="manualReconnect"
    />
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import TopicControls from './TopicControls.vue'
import StatusBar from './StatusBar.vue'
import MessageFeed from './MessageFeed.vue'
import { getStreamHealth, getStreamTopics } from '../../api.js'

const health = ref({ status: '', kafka: '' })
const topics = ref([])
const selectedTopic = ref('')
const messages = ref([])
const prettyPrint = ref(false)
const isPaused = ref(false)
const error = ref('')
const info = ref('')
const warning = ref('')
const topicConnected = ref(false)
const isConnecting = ref(false)

const offset = ref('')
const since = ref('')
const limit = ref('')

const rateCurrent = ref('..')
const rateAverage = ref('..')
const connectionDuration = ref('0s')

let eventSource = null
let freqChecker = null
let reconnectTimeout = null
let reconnectAttempts = 0
const MAX_RECONNECT_ATTEMPTS = 10
const INITIAL_RECONNECT_DELAY = 1000
let messageCount = 0
let totalMessages = 0
let connectionStartTime = null
let lastCheck = Date.now()
let isManualClose = false

const streamUrl = computed(() => {
  if (!selectedTopic.value) return ''
  let url = `/v1/streams/${selectedTopic.value}`
  const params = []
  if (offset.value !== '') params.push(`offset=${offset.value}`)
  if (since.value) params.push(`since=${since.value}`)
  if (limit.value !== '') params.push(`limit=${limit.value}`)
  if (params.length > 0) url += '?' + params.join('&')
  return url
})

const formattedMessages = computed(() => {
  return messages.value.map((msg) => {
    const cleanMsg = msg.replace(/^data: /, '')
    if (prettyPrint.value) {
      try {
        return JSON.stringify(JSON.parse(cleanMsg), null, 2)
      } catch {
        return cleanMsg
      }
    }
    return cleanMsg
  })
})

async function fetchTopics() {
  error.value = ''
  info.value = 'Loading topics...'
  try {
    topics.value = await getStreamTopics()
    if (topics.value.includes('entity_change') && !selectedTopic.value) {
      selectedTopic.value = 'entity_change'
    }
    if (topics.value.length === 0) {
      info.value = 'No topics found. Is the stream backend running?'
    } else {
      info.value = ''
    }
  } catch (e) {
    error.value = `Failed to load topics: ${e.message}`
    info.value = ''
  }
}

async function fetchHealth() {
  try {
    health.value = await getStreamHealth()
  } catch {
    health.value = { status: 'unknown', kafka: 'disconnected' }
  }
}

function connectToStream() {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }

  if (!selectedTopic.value) {
    warning.value = 'Select a topic to view messages'
    return
  }

  messages.value = []
  messageCount = 0
  totalMessages = 0
  lastCheck = Date.now()
  isConnecting.value = true
  info.value = ''
  warning.value = ''
  error.value = ''
  isManualClose = false
  reconnectAttempts = 0

  eventSource = new EventSource(streamUrl.value)

  eventSource.onopen = () => {
    isConnecting.value = false
    topicConnected.value = true
    connectionStartTime = Date.now()
    totalMessages = 0
    reconnectAttempts = 0
    startRateChecker()
  }

  eventSource.onmessage = (msg) => {
    messageCount++
    totalMessages++
    if (!isPaused.value) {
      messages.value.unshift(msg.data)
      if (messages.value.length > 200) {
        messages.value.pop()
      }
    }
  }

  eventSource.onerror = () => {
    isConnecting.value = false
    error.value = 'Connection error'
    info.value = ''
    topicConnected.value = false
    connectionStartTime = null
    stopRateChecker()
    attemptReconnect()
  }
}

function attemptReconnect() {
  if (isManualClose || reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      error.value = `Failed to reconnect after ${MAX_RECONNECT_ATTEMPTS} attempts. Please reconnect manually.`
    }
    return
  }

  const delay = Math.min(
    INITIAL_RECONNECT_DELAY * Math.pow(2, reconnectAttempts),
    30000
  )
  reconnectAttempts++
  info.value = `Reconnecting in ${delay / 1000}s... (attempt ${reconnectAttempts})`

  reconnectTimeout = setTimeout(() => {
    if (!isManualClose && selectedTopic.value) {
      connectToStream()
    }
  }, delay)
}

function startRateChecker() {
  stopRateChecker()
  freqChecker = setInterval(() => {
    const now = Date.now()
    const elapsed = now - lastCheck
    if (elapsed >= 1000) {
      rateCurrent.value = messageCount
      if (connectionStartTime) {
        const secondsElapsed = (now - connectionStartTime) / 1000
        rateAverage.value = Math.round(totalMessages / secondsElapsed)
        const totalSecs = Math.floor(secondsElapsed)
        const mins = Math.floor(totalSecs / 60)
        const secs = totalSecs % 60
        connectionDuration.value = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
      }
      messageCount = 0
      lastCheck = now
    }
  }, 100)
}

function stopRateChecker() {
  if (freqChecker) {
    clearInterval(freqChecker)
    freqChecker = null
  }
}

async function copyMessages() {
  if (messages.value.length === 0) {
    info.value = 'No messages to copy'
    return
  }
  try {
    await navigator.clipboard.writeText(messages.value.join('\n'))
    info.value = 'Messages copied to clipboard!'
  } catch {
    info.value = 'Failed to copy messages'
  }
}

function clearMessages() {
  messages.value = []
}

function manualReconnect() {
  if (reconnectTimeout) clearTimeout(reconnectTimeout)
  isManualClose = false
  reconnectAttempts = 0
  connectToStream()
}

watch(selectedTopic, () => {
  if (selectedTopic.value) {
    isManualClose = false
    connectToStream()
  }
})

onMounted(() => {
  fetchHealth()
  fetchTopics()
})

onUnmounted(() => {
  isManualClose = true
  if (reconnectTimeout) clearTimeout(reconnectTimeout)
  if (eventSource) eventSource.close()
  stopRateChecker()
})
</script>

<style scoped>
.stream-panel {
  max-width: 60rem;
}

.stream-info {
  padding: 0.5rem 1rem;
  background: #eef6ff;
  border: 1px solid #b6d4fe;
  border-radius: 8px;
  margin: 1rem 0;
}
</style>
