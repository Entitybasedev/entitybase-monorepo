<script setup>
import { onMounted, ref } from 'vue'
import { infrastructure, workers, producers, streamingServices, HOST } from './config/services.js'
import { useHealth } from './composables/useHealth.js'
import StatusCard from './components/StatusCard.vue'

const version = import.meta.env.VITE_APP_VERSION || 'dev'
const uptime = ref('')

const { getStatus, checkAll, fetchSettings } = useHealth()

function formatUptime(seconds) {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return `${hours}h ${minutes}m`
}

async function fetchUptime() {
  try {
    const res = await fetch(`http://${HOST}:8083/v1/uptime`)
    if (!res.ok) return
    const data = await res.json()
    uptime.value = formatUptime(data.uptime_seconds)
  } catch {
    uptime.value = ''
  }
}

onMounted(async () => {
  await fetchSettings()
  await checkAll(infrastructure)
  await checkAll(streamingServices)
  await checkAll(producers)
  await checkAll(workers)
  await fetchUptime()

  setInterval(async () => {
    await checkAll(infrastructure)
    await checkAll(streamingServices)
    await checkAll(producers)
    await checkAll(workers)
    await fetchUptime()
  }, 30000)
})
</script>

<template>
  <div class="container">
    <header>
      <img src="/entitybase-logo.png" alt="Entitybase" class="logo" />
      <h1>Entitybase Orchestrator</h1>
    </header>

    <section>
      <h2>Infrastructure</h2>
      <div class="grid">
        <template v-for="item in infrastructure" :key="item.url">
          <StatusCard
            :name="item.name"
            :url="item.url"
            :description="item.description"
            :status="getStatus(item)"
            :link-url="item.linkUrl"
          />
        </template>
      </div>
    </section>

    <section>
      <h2>Event Streaming</h2>
      <div class="grid">
        <template v-for="item in streamingServices" :key="item.url">
          <StatusCard
            :name="item.name"
            :url="item.url"
            :description="item.description"
            :status="getStatus(item)"
            :link-url="item.linkUrl"
          />
        </template>
        <template v-for="item in producers" :key="item.producerKey">
          <StatusCard
            :name="item.name"
            :url="item.url"
            :description="item.description"
            :status="getStatus(item)"
            :is-producer="true"
            :topic="item.topic"
            :link-url="item.linkUrl"
          />
        </template>
      </div>
    </section>

    <section>
      <h2>Workers</h2>
      <div class="grid">
        <template v-for="item in workers" :key="item.url">
          <StatusCard
            :name="item.name"
            :url="item.url"
            :status="getStatus(item)"
            section-class="worker"
          />
        </template>
      </div>
    </section>

    <footer class="legend">
      <span class="legend-item"><span class="dot healthy"></span> Healthy</span>
      <span class="legend-item"><span class="dot unhealthy"></span> Unhealthy</span>
      <span class="legend-item"><span class="dot disabled"></span> Disabled</span>
      <span class="version">{{ version }}</span>
      <span v-if="uptime" class="uptime" title="Uptime for the Entitybase API">Up: {{ uptime }}</span>
    </footer>
  </div>
</template>

<style scoped>
.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
}

header {
  text-align: center;
  margin-bottom: 3rem;
}

.logo {
  max-width: 400px;
  width: 100%;
  height: auto;
  margin-bottom: 1rem;
}

h1 {
  font-size: 2rem;
  color: #333;
  margin: 0;
}

.legend {
  display: flex;
  justify-content: center;
  gap: 1.5rem;
  margin-top: 1rem;
  font-size: 0.9rem;
  color: #666;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.dot.healthy { background: #22c55e; }
.dot.unhealthy { background: #ef4444; }
.dot.disabled { background: #f59e0b; }

.uptime {
  color: #22c55e;
}

h2 {
  font-size: 1.5rem;
  color: #555;
  margin-bottom: 1rem;
  margin-top: 2rem;
  padding-bottom: 0.5rem;
  text-align: center;
  border-bottom: 1px solid #eee;
}

.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

:deep(.worker) {
  background: #f9f9f9;
}
</style>