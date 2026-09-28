<template>
  <div>
    <div class="actions">
      <label>
        <input :checked="prettyPrint" @change="$emit('update:prettyPrint', $event.target.checked)" type="checkbox" />
        Pretty print
      </label>
      <label>
        <input :checked="isPaused" @change="$emit('update:isPaused', $event.target.checked)" type="checkbox" />
        Pause
      </label>
      <button @click="$emit('copy')">Copy</button>
      <button @click="$emit('clear')">Clear</button>
      <button @click="$emit('reconnect')">Reconnect</button>
    </div>

    <pre class="feed"><code v-for="(msg, i) in messages" :key="i" v-html="msg"></code></pre>
  </div>
</template>

<script setup>
defineProps({
  messages: Array,
  prettyPrint: Boolean,
  isPaused: Boolean
})

defineEmits(['update:prettyPrint', 'update:isPaused', 'copy', 'clear', 'reconnect'])
</script>

<style scoped>
.actions {
  display: flex;
  gap: 15px;
  align-items: center;
  margin-bottom: 15px;
}

.actions label {
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
}

.actions button {
  padding: 6px 12px;
  background: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.actions button:hover {
  background: #218838;
}

.feed {
  max-height: 500px;
  overflow-y: auto;
  background: #f9f9f9;
  border: 1px solid #ddd;
  padding: 10px;
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-all;
}

.feed code {
  display: block;
}
</style>