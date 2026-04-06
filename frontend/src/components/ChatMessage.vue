<template>
  <div class="message-row" :class="message.role">
    <div class="message-bubble">
      <div
        v-if="message.role === 'assistant' && message.thinking?.trim()"
        class="thinking-box"
      >
        <div v-if="message.showThinking" class="thinking-title">处理中</div>
        <div
          ref="thinkingRef"
          class="thinking-content markdown-body"
          @scroll="handleThinkingScroll"
          v-html="renderMarkdown(message.thinking)"
        />
      </div>

      <div
        v-if="message.content"
        class="message-content markdown-body"
        v-html="renderMarkdown(message.content)"
      />

      <div v-if="message.loading" class="loading-text">
        正在生成...
      </div>

      <div
        v-if="
          message.role === 'assistant' &&
          !message.loading &&
          message.evidenceReady &&
          message.evidence?.length
        "
        class="message-actions"
      >
        <el-button
          size="small"
          plain
          round
          class="evidence-btn"
          @click="emit('open-evidence', message)"
        >
          查看证据
        </el-button>
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref, watch, nextTick } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

const props = defineProps({
  message: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['open-evidence'])

const md = new MarkdownIt({
  breaks: true,
  linkify: true
})

const renderMarkdown = (text) => {
  const raw = md.render(text || '')
  return DOMPurify.sanitize(raw)
}

const thinkingRef = ref(null)
const shouldAutoScrollThinking = ref(true)
const thinkingProgrammaticScrolling = ref(false)

const isNearBottom = (el, threshold = 24) => {
  return el.scrollHeight - el.scrollTop - el.clientHeight <= threshold
}

const scrollThinkingToBottom = async () => {
  await nextTick()
  const el = thinkingRef.value
  if (!el || !shouldAutoScrollThinking.value) return

  thinkingProgrammaticScrolling.value = true
  el.scrollTop = el.scrollHeight

  requestAnimationFrame(() => {
    thinkingProgrammaticScrolling.value = false
  })
}

const handleThinkingScroll = () => {
  const el = thinkingRef.value
  if (!el || thinkingProgrammaticScrolling.value) return
  shouldAutoScrollThinking.value = isNearBottom(el)
}

watch(
  () => props.message.thinking,
  async () => {
    await scrollThinkingToBottom()
  },
  { flush: 'post' }
)
</script>

<style scoped>
.message-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.evidence-btn {
  border-color: #d1d5db !important;
  color: #475569 !important;
  background: #fff !important;
}

.evidence-btn:hover {
  border-color: #22c55e !important;
  color: #16a34a !important;
}

.message-row {
  display: flex;
  width: 100%;
  margin-bottom: 16px;
  box-sizing: border-box;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

.message-bubble {
  box-sizing: border-box;
  width: fit-content;
  padding: 14px 16px;
  border-radius: 18px;
  word-break: break-word;
  line-height: 1.7;
}

.message-row.user .message-bubble {
  margin-left: auto;
  max-width: 42%;
  background: linear-gradient(135deg, #dcfce7, #c8f1d7);
  color: #1f2937;
  border-top-right-radius: 6px;
  box-shadow: 0 8px 20px rgba(34, 197, 94, 0.12);
}

.message-row.assistant .message-bubble {
  margin-right: auto;
  max-width: 62%;
  background: #ffffff;
  color: #1f2937;
  border: 1px solid #e5e7eb;
  border-top-left-radius: 6px;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
}

.thinking-box {
  margin-bottom: 12px;
  padding: 12px 14px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
}

.thinking-title {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 8px;
  font-weight: 600;
}

.thinking-content {
  max-height: 140px;
  overflow-y: auto;
  font-size: 13px;
  color: #475569;
  line-height: 1.7;
}

.message-content {
  font-size: 14px;
  color: #1f2937;
  line-height: 1.8;
}

.loading-text {
  margin-top: 8px;
  font-size: 13px;
  color: #94a3b8;
}

.message-content,
.thinking-content {
  white-space: normal;
}

.markdown-body :deep(*:first-child) {
  margin-top: 0 !important;
}

.markdown-body :deep(*:last-child) {
  margin-bottom: 0 !important;
}

.markdown-body :deep(p) {
  margin: 0 0 10px;
}

.markdown-body :deep(strong) {
  font-weight: 700;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 8px 0;
  padding-left: 22px;
}

.markdown-body :deep(li) {
  margin: 4px 0;
}

.markdown-body :deep(li > p) {
  margin: 0;
}

.markdown-body :deep(code) {
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 6px;
  font-size: 12px;
}

.markdown-body :deep(pre) {
  background: #f8fafc;
  padding: 12px;
  border-radius: 12px;
  overflow-x: auto;
  border: 1px solid #e5e7eb;
}

.markdown-body :deep(pre code) {
  background: transparent;
  padding: 0;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  margin: 14px 0 8px;
  line-height: 1.45;
  color: #111827;
}

.thinking-content::-webkit-scrollbar {
  width: 6px;
}

.thinking-content::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.4);
  border-radius: 999px;
}

@media (max-width: 768px) {
  .message-row.user .message-bubble {
    max-width: 78%;
  }

  .message-row.assistant .message-bubble {
    max-width: 86%;
  }
}
</style>