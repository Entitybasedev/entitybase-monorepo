<template>
  <div class="stream-status" data-testid="stream-status">
    <span>Status:</span>
    <span v-if="health.status" class="backend-status">
      Stream backend: {{ health.status }}
    </span>
    <span
      v-if="health.kafka"
      class="kafka-status"
      :title="
        'Connected to ' +
        (health.backend_type === 'unknown' ? 'Kafka-compatible' : health.backend_type)
      "
    >
      Streaming backend: {{ health.kafka }}
    </span>
    <span v-if="isConnecting || topicConnected" class="topic-status">
      Topic: {{ isConnecting ? 'connecting' : 'connected' }}
      <span v-if="isConnecting" class="spinner"></span>
    </span>
    <span v-if="topicConnected" class="duration">({{ connectionDuration }})</span>
    <span class="rate-spacer"></span>
    <span data-testid="stream-rate">Events/sec: {{ rateCurrent }}</span>
    <span>(avg: {{ rateAverage }}/s)</span>
  </div>
</template>

<script setup>
defineProps({
  health: Object,
  topicConnected: Boolean,
  isConnecting: Boolean,
  connectionDuration: String,
  rateCurrent: String,
  rateAverage: String,
})
</script>

<style scoped>
.stream-status {
  display: flex;
  align-items: center;
  padding: 10px;
  background: #e9ecef;
  border-radius: 4px;
  margin-bottom: 15px;
  overflow-x: auto;
  white-space: nowrap;
}

.stream-status span {
  margin-right: 15px;
  flex-shrink: 0;
}

.stream-status > span:first-child {
  font-weight: bold;
}

.rate-spacer {
  flex-grow: 1;
}

.backend-status,
.kafka-status,
.topic-status {
  color: #28a745;
}

.topic-status {
  display: flex;
  align-items: center;
  gap: 6px;
}

.duration {
  color: #666;
}

.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid #666;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
