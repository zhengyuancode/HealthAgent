<template>
  <div class="message-bubble" :class="messageClass">
    <div class="message-content">{{ message.content }}</div>
    <div class="message-timestamp">{{ formattedTime }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  message: {
    type: Object,
    required: true
  }
})

const messageClass = computed(() => {
  return props.message.role === 'user' ? 'user-message' : 'ai-message'
})

const formattedTime = computed(() => {
  const date = new Date(props.message.timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
})
</script>

<style scoped>
.message-bubble {
  margin-bottom: 15px;
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 12px;
  word-wrap: break-word;
  position: relative;
}

.user-message {
  background-color: white;
  border: 1px solid var(--primary-green);
  margin-left: auto;
  border-radius: 12px 0 12px 12px;
}

.ai-message {
  background-color: var(--light-green-bg);
  margin-right: auto;
  border-radius: 0 12px 12px 12px;
}

.message-content {
  font-size: 14px;
  line-height: 1.5;
}

.message-timestamp {
  font-size: 12px;
  color: var(--secondary-text);
  margin-top: 4px;
  text-align: right;
}
</style>