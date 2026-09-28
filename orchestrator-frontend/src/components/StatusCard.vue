<script setup>
defineProps({
  name: { type: String, required: true },
  url: { type: String, required: true },
  description: { type: String, default: '' },
  status: { type: String, default: 'unhealthy' },
  linkUrl: { type: String, default: '' },
  isProducer: { type: Boolean, default: false },
  topic: { type: String, default: '' },
  sectionClass: { type: String, default: '' },
})
</script>

<template>
  <a
    v-if="linkUrl"
    :href="linkUrl"
    class="status-card"
    :class="sectionClass"
    target="_blank"
  >
    <div class="card-header">
      <h3>{{ name }}</h3>
      <span class="status" :class="status"></span>
    </div>
    <p v-if="description">{{ description }}</p>
    <span v-if="topic" class="topic">Topic: {{ topic }}</span>
    <span class="url">{{ url }}</span>
  </a>
  <div
    v-else-if="isProducer"
    class="status-card producer"
  >
    <div class="card-header">
      <h3>{{ name }}</h3>
      <span class="status" :class="status"></span>
    </div>
    <p v-if="description">{{ description }}</p>
    <span v-if="topic" class="topic">Topic: {{ topic }}</span>
    <span class="url">{{ url }}</span>
  </div>
  <a
    v-else
    :href="url"
    class="status-card"
    target="_blank"
  >
    <div class="card-header">
      <h3>{{ name }}</h3>
      <span class="status" :class="status"></span>
    </div>
    <p v-if="description">{{ description }}</p>
    <span class="url">{{ url }}</span>
  </a>
</template>

<style scoped>
.status-card {
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  text-decoration: none;
  color: inherit;
  transition: box-shadow 0.2s, transform 0.2s;
  background: #fff;
}

.status-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.status-card h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.1rem;
}

.status {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status.healthy { background: #22c55e; }
.status.unhealthy { background: #ef4444; }
.status.disabled { background: #f59e0b; }
.status.disconnected { background: #ef4444; }
.status.connected { background: #22c55e; }

.status-card p {
  margin: 0 0 0.5rem 0;
  color: #666;
  font-size: 0.9rem;
}

.topic {
  font-size: 0.75rem;
  color: #0066cc;
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.url {
  font-size: 0.8rem;
  color: #888;
  margin-top: auto;
}

</style>