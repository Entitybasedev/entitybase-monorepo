<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import StatusBar from './components/StatusBar.vue'
import TopicControls from './components/TopicControls.vue'
import MessageFeed from './components/MessageFeed.vue'

const backendUrl = ref(import.meta.env.KAFKA2SSE_BACKEND_URL || 'http://localhost:8888')
const version = ref(import.meta.env.VITE_APP_VERSION || 'dev')
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
  let url = `${backendUrl.value}/v1/streams/${selectedTopic.value}`
  const params = []
  if (offset.value !== '') params.push(`offset=${offset.value}`)
  if (since.value) params.push(`since=${since.value}`)
  if (limit.value !== '') params.push(`limit=${limit.value}`)
  if (params.length > 0) url += '?' + params.join('&')
  return url
})

const formattedMessages = computed(() => {
  return messages.value.map(msg => {
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
    const res = await fetch(`${backendUrl.value}/v1/topics`)
    const data = await res.json()
    topics.value = data.topics || []
    if (topics.value.includes('entity_change') && !selectedTopic.value) {
      selectedTopic.value = 'entity_change'
    }
    if (topics.value.length === 0) {
      info.value = 'No topics found. Is the backend running?'
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
    const res = await fetch(`${backendUrl.value}/health`)
    const data = await res.json()
    health.value = data
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

  const delay = Math.min(INITIAL_RECONNECT_DELAY * Math.pow(2, reconnectAttempts), 30000)
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
    alert('No messages to copy')
    return
  }
  try {
    await navigator.clipboard.writeText(messages.value.join('\n'))
    alert('Messages copied to clipboard!')
  } catch {
    alert('Failed to copy messages')
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

watch(backendUrl, () => {
  fetchHealth()
  fetchTopics()
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

<template>
  <div class="container">
    <h1>Kafka2SSE</h1>
    
    <TopicControls 
      :backend-url="backendUrl"
      :topics="topics"
      :selected-topic="selectedTopic"
      :offset="offset"
      :since="since"
      :limit="limit"
      @update:backendUrl="backendUrl = $event"
      @update:selectedTopic="selectedTopic = $event"
      @update:offset="offset = $event"
      @update:since="since = $event"
      @update:limit="limit = $event"
      @refresh="fetchTopics"
    />

    <div v-if="error" class="alert error">{{ error }}</div>
    <div v-if="info" class="alert info">{{ info }}</div>
    <div v-if="warning" class="alert warning">{{ warning }}</div>

    <StatusBar 
      :health="health"
      :topic-connected="topicConnected"
      :is-connecting="isConnecting"
      :connection-duration="connectionDuration"
      :rate-current="rateCurrent"
      :rate-average="rateAverage"
    />

    <MessageFeed 
      :messages="formattedMessages"
      :pretty-print="prettyPrint"
      :is-paused="isPaused"
      @update:prettyPrint="prettyPrint = $event"
      @update:isPaused="isPaused = $event"
      @copy="copyMessages"
      @clear="clearMessages"
      @reconnect="manualReconnect"
    />

    <div class="footer">
      <span class="version">v{{ version }}</span>
    </div>
  </div>
</template>

<style>
* {
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  margin: 0;
  padding: 20px;
  background: #f5f5f5;
}

.container {
  max-width: 1100px;
  margin: 0 auto;
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

h1 {
  margin-top: 0;
  color: #333;
  text-align: center;
}

.version {
  font-size: 0.5em;
  color: #666;
  font-weight: normal;
  padding: 2px 8px;
  border-radius: 4px;
}

.version.ok {
  background: #d4edda;
  color: #155724;
}

.version.degraded {
  background: #fff3cd;
  color: #856404;
}

.alert {
  padding: 10px 15px;
  border-radius: 4px;
  margin-bottom: 15px;
}

.alert.error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.alert.info {
  background: #d1ecf1;
  color: #0c5460;
  border: 1px solid #bee5eb;
}

.alert.warning {
  background: #fff3cd;
  color: #856404;
  border: 1px solid #ffeeba;
}

.footer {
  text-align: center;
  padding: 10px;
  font-size: 12px;
  color: #666;
  border-top: 1px solid #ddd;
  margin-top: 10px;
}

.footer .version {
  color: #888;
}
</style>