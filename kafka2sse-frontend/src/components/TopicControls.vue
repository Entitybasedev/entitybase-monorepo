<template>
  <div class="controls">
    <div class="control-group">
      <label>Backend URL:</label>
      <input :value="backendUrl" @input="$emit('update:backendUrl', $event.target.value)" type="text" @change="$emit('refresh')" />
      <button @click="$emit('refresh')">Refresh Topics</button>
    </div>

    <div class="control-group">
      <label>Topic:</label>
      <select :value="selectedTopic" @change="$emit('update:selectedTopic', $event.target.value)">
        <option value="">Select a topic...</option>
        <option v-for="topic in topics" :key="topic" :value="topic">
          {{ topic }}
        </option>
      </select>
    </div>

    <div class="control-group">
      <label>Offset:</label>
      <input :value="offset" @input="$emit('update:offset', $event.target.value)" type="number" placeholder="0 for earliest" min="0" />
    </div>

    <div class="control-group">
      <label title="ISO8601 format (e.g., 2026-03-05T12:00:00Z)">Since:</label>
      <input :value="since" @input="$emit('update:since', $event.target.value)" type="text" placeholder="2026-03-05T12:00:00Z" />
    </div>

    <div class="control-group">
      <label>Limit:</label>
      <input :value="limit" @input="$emit('update:limit', $event.target.value)" type="number" placeholder="no limit" min="0" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  backendUrl: String,
  topics: Array,
  selectedTopic: String,
  offset: String,
  since: String,
  limit: String
})

defineEmits(['update:backendUrl', 'update:selectedTopic', 'update:offset', 'update:since', 'update:limit', 'refresh'])
</script>

<style scoped>
.controls {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  margin-bottom: 15px;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-group label {
  font-weight: bold;
}

.control-group input[type="text"] {
  color: #111;
  padding: 6px 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  width: 250px;
}

.control-group select {
  padding: 6px 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  min-width: 200px;
}

.control-group input[type="number"] {
  color: #111;
  padding: 6px 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  width: 150px;
}

.control-group input::placeholder {
  color: #666;
}

.control-group button {
  padding: 6px 12px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.control-group button:hover {
  background: #0056b3;
}
</style>