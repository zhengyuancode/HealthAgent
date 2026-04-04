<template>
  <div class="message-row" :class="message.role">
    <div class="message-bubble">
      <div
        v-if="message.role === 'assistant' && message.showThinking && message.thinking?.trim()"
        class="thinking-box"
      >
        <div class="thinking-title">处理中</div>
        <div class="thinking-content">
          {{ message.thinking }}
        </div>
      </div>

      <div v-if="message.content" class="message-content">
        {{ message.content }}
      </div>

      <div v-if="message.loading && !message.content" class="loading-text">
        正在生成...
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  message: {
    type: Object,
    required: true
  }
})
</script>

<style scoped>
.message-row {
  display: flex;
  margin-bottom: 16px;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 80%;
  padding: 12px 14px;
  border-radius: 12px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
}

.message-row.user .message-bubble {
  background: #dff6e8;
}

.message-row.assistant .message-bubble {
  background: #fff;
  border: 1px solid #eee;
}

.thinking-box {
  margin-bottom: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f6f7f9;
  border: 1px solid #e5e7eb;
}

.thinking-title {
  font-size: 12px;
  color: #666;
  margin-bottom: 6px;
}

.thinking-content {
  max-height: 120px;
  overflow-y: auto;
  font-size: 13px;
  color: #444;
  white-space: pre-wrap;
}

.message-content {
  font-size: 14px;
  color: #222;
  white-space: pre-wrap;
}

.loading-text {
  font-size: 13px;
  color: #999;
}
</style>