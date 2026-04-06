<template>
  <div class="chat-container">
    <aside class="chat-sidebar">
      <div class="sidebar-top">
        <div class="brand-block">
          <div class="brand-logo">AI</div>
          <div class="brand-text">
            <h2>智能医疗助手</h2>
            <p>您身边的医疗专家</p>
          </div>
        </div>

        <el-button
          type="primary"
          class="new-dialog-btn"
          @click="newDialog"
        >
          + 新建对话
        </el-button>
      </div>

      <div class="sidebar-section-title">历史会话</div>

      <div class="dialog-list">
        <div
          v-for="(dialog, index) in dialogs"
          :key="dialog.id"
          class="dialog-item"
          :class="{ active: selectedIndex === index }"
          @click="switchDialog(index)"
        >
          <div class="dialog-main">
            <div class="dialog-item-title">{{ dialog.title }}</div>
            <div class="dialog-item-desc">
              {{ dialog.messageCount ? `${dialog.messageCount} 条消息` : '暂无消息' }}
            </div>
          </div>

          <el-button
            type="danger"
            text
            class="delete-dialog-btn"
            @click.stop="handleDeleteDialog(dialog.id, index)"
          >
            删除
          </el-button>
        </div>
      </div>

      <div class="user-info">
        <div class="user-card">
          <div class="user-avatar">
            {{ (userInfo?.username || 'U').slice(0, 1).toUpperCase() }}
          </div>
          <div class="user-meta">
            <div class="user-label">当前用户</div>
            <div class="username">{{ userInfo?.username || '未登录用户' }}</div>
          </div>
        </div>

        <el-button
          type="danger"
          plain
          class="logout-btn"
          @click="handleLogout"
        >
          退出登录
        </el-button>
      </div>
    </aside>

    <main class="chat-main">
      <div class="chat-main-header">
        <div>
          <div class="header-title">
            {{ currentDialog?.title || '新对话' }}
          </div>
          <div class="header-subtitle">
            Enter 发送，Ctrl / ⌘ + Enter 换行
          </div>
        </div>
      </div>

      <div
        ref="messagesRef"
        class="chat-messages"
        @scroll="handleMessagesScroll"
      >
        <div class="messages-inner">
          <div v-if="!currentMessages.length" class="chat-empty">
            <div class="empty-icon">💬</div>
            <div class="empty-title">开始一段新的医疗咨询</div>
            <div class="empty-desc">
              你可以输入症状、疾病、检查项目或政策相关问题
            </div>
          </div>

          <ChatMessage
            v-for="(message, index) in currentMessages"
            v-else
            :key="message.id || index"
            :message="message"
            @open-evidence="openEvidenceDrawer"
          />
        </div>
      </div>

      <div class="chat-input-shell">
        <div class="chat-input-area">
          <el-input
            v-model="inputMessage"
            type="textarea"
            class="chat-input"
            placeholder="请输入你的问题..."
            :rows="3"
            @keydown="handleKeyDown"
          />
          <el-button
            type="primary"
            class="send-button"
            :disabled="isGenerating"
            @click="sendMessage"
          >
            <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>
      <el-drawer
        v-model="evidenceDrawerVisible"
        title="证据来源"
        direction="rtl"
        size="420px"
        class="evidence-drawer"
      >
        <div v-if="activeEvidenceList.length" class="evidence-list">
          <div
            v-for="(item, idx) in activeEvidenceList"
            :key="idx"
            class="evidence-card"
          >
            <div class="evidence-header">
              <div class="evidence-source">{{ item.source || '未知来源' }}</div>
              <div v-if="item.score !== undefined" class="evidence-score">
                相关度：{{ Number(item.score).toFixed(3) }}
              </div>
            </div>

            <div v-if="item.title" class="evidence-title">
              {{ item.title }}
            </div>

            <div class="evidence-content">
              {{ item.content || '暂无证据内容' }}
            </div>
          </div>
        </div>

        <el-empty v-else description="暂无证据" />
      </el-drawer>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useChatStream } from '@/composables/useChatStream'
import {
  getChatSessions,
  getChatMessages,
  createChatSession,
  deleteChatSession
} from '@/api/chat'
import ChatMessage from '@/components/ChatMessage.vue'
import { ArrowRight } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()

const inputMessage = ref('')
const dialogs = ref([])
const selectedIndex = ref(0)

const currentDialog = computed(() => dialogs.value[selectedIndex.value] || null)

const currentMessages = computed(() => {
  return currentDialog.value?.messages || []
})

const userInfo = computed(() => userStore.userInfo)

const { isGenerating, sendMessage: streamSendMessage } = useChatStream()

const messagesRef = ref(null)
const shouldAutoScrollMessages = ref(true)
const programmaticScrolling = ref(false)

const evidenceDrawerVisible = ref(false)
const activeEvidenceList = ref([])

const isNearBottom = (el, threshold = 40) => {
  return el.scrollHeight - el.scrollTop - el.clientHeight <= threshold
}

const scrollMessagesToBottom = async () => {
  await nextTick()
  const el = messagesRef.value
  if (!el || !shouldAutoScrollMessages.value) return

  programmaticScrolling.value = true
  el.scrollTop = el.scrollHeight

  requestAnimationFrame(() => {
    programmaticScrolling.value = false
  })
}

const handleMessagesScroll = () => {
  const el = messagesRef.value
  if (!el || programmaticScrolling.value) return
  shouldAutoScrollMessages.value = isNearBottom(el)
}

const mapMessage = (item) => ({
  id: item.id,
  role: item.role,
  content: item.content,
  thinking: '',
  showThinking: true,
  loading: false,
  evidence: [],
  evidenceReady: false,
  createdAt: item.created_at
})

const loadMessages = async (sessionId) => {
  const res = await getChatMessages(sessionId)
  const dialog = dialogs.value.find((d) => d.id === sessionId)
  if (!dialog) return

  dialog.messages = (res || []).map(mapMessage)
  dialog.messageCount = dialog.messages.length
  dialog.loaded = true
}

const loadSessions = async () => {
  const res = await getChatSessions()

  dialogs.value = (res || []).map((item) => ({
    id: item.id,
    title: item.title || '新对话',
    messageCount: item.message_count || 0,
    messages: [],
    loaded: false
  }))

  if (!dialogs.value.length) {
    const newSession = await createChatSession({ title: '新对话' })
    dialogs.value = [{
      id: newSession.id,
      title: newSession.title || '新对话',
      messageCount: 0,
      messages: [],
      loaded: true
    }]
    selectedIndex.value = 0
    return
  }

  selectedIndex.value = 0
  await loadMessages(dialogs.value[0].id)
}

watch(
  () =>
    currentMessages.value
      .map(
        (m) =>
          `${m.role}-${m.content?.length || 0}-${m.thinking?.length || 0}-${m.loading ? 1 : 0}`
      )
      .join('|'),
  async () => {
    await scrollMessagesToBottom()
  },
  { flush: 'post' }
)

const newDialog = async () => {
  const res = await createChatSession({ title: '新对话' })

  dialogs.value.unshift({
    id: res.id,
    title: res.title || '新对话',
    messageCount: 0,
    messages: [],
    loaded: true
  })

  selectedIndex.value = 0
  shouldAutoScrollMessages.value = true
  await scrollMessagesToBottom()
}

const switchDialog = async (index) => {
  selectedIndex.value = index
  const dialog = dialogs.value[index]

  if (dialog && !dialog.loaded) {
    await loadMessages(dialog.id)
  }

  shouldAutoScrollMessages.value = true
  await scrollMessagesToBottom()
}

const handleDeleteDialog = async (sessionId, index) => {
  try {
    await ElMessageBox.confirm(
      '确认删除这个会话吗？删除后不可恢复。',
      '删除会话',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deleteChatSession(sessionId)

    const isDeletingCurrent = selectedIndex.value === index

    dialogs.value.splice(index, 1)

    if (!dialogs.value.length) {
      const newSession = await createChatSession({ title: '新对话' })
      dialogs.value = [
        {
          id: newSession.id,
          title: newSession.title || '新对话',
          messageCount: 0,
          messages: [],
          loaded: true
        }
      ]
      selectedIndex.value = 0
      activeEvidenceList.value = []
      evidenceDrawerVisible.value = false
      ElMessage.success('删除成功')
      return
    }

    if (isDeletingCurrent) {
      const nextIndex = Math.min(index, dialogs.value.length - 1)
      selectedIndex.value = nextIndex

      const nextDialog = dialogs.value[nextIndex]
      if (nextDialog && !nextDialog.loaded) {
        await loadMessages(nextDialog.id)
      }
    } else if (selectedIndex.value > index) {
      selectedIndex.value -= 1
    }

    activeEvidenceList.value = []
    evidenceDrawerVisible.value = false
    shouldAutoScrollMessages.value = true
    await scrollMessagesToBottom()

    ElMessage.success('删除成功')
  } catch (error) {
    if (error === 'cancel' || error === 'close') return

    console.error('删除会话失败:', error)
    ElMessage.error('删除会话失败')
  }
}

const sendMessage = async () => {
  const text = inputMessage.value.trim()
  if (!text || isGenerating.value || !currentDialog.value) return

  inputMessage.value = ''

  try {
    shouldAutoScrollMessages.value = true
    await streamSendMessage(currentDialog.value.id, currentMessages.value, text)

    currentDialog.value.messageCount = currentMessages.value.length

    if (!currentDialog.value.title || currentDialog.value.title === '新对话') {
      currentDialog.value.title = text.slice(0, 20)
    }
  } catch (error) {
    console.error('发送消息失败:', error)
  }
}

const handleKeyDown = (event) => {
  if (event.key === 'Enter') {
    if (event.ctrlKey || event.metaKey) {
      inputMessage.value += '\n'
    } else {
      event.preventDefault()
      sendMessage()
    }
  }
}

const handleLogout = () => {
  userStore.clearToken()
  router.push('/login')
}

const openEvidenceDrawer = (message) => {
  activeEvidenceList.value = message?.evidence || []
  evidenceDrawerVisible.value = true
}

onMounted(async () => {
  try {
    await loadSessions()
  } catch (error) {
    console.error('加载历史会话失败:', error)
  }
})
</script>

<style scoped>
.chat-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background:
    radial-gradient(circle at top left, #f4f8ff 0%, #eef3f8 38%, #e9eef5 100%);
  color: #1f2937;
}

/* =======================
   Sidebar
======================= */
.chat-sidebar {
  width: 290px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 20px 16px;
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(18px);
  border-right: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 6px 0 24px rgba(15, 23, 42, 0.04);
}

.sidebar-top {
  margin-bottom: 18px;
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
  padding: 10px 8px;
}

.brand-logo {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #22c55e, #16a34a);
  box-shadow: 0 10px 24px rgba(34, 197, 94, 0.28);
}

.brand-text h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #111827;
}

.brand-text p {
  margin: 4px 0 0;
  font-size: 12px;
  color: #6b7280;
}

.new-dialog-btn {
  width: 100%;
  height: 44px;
  border: none !important;
  border-radius: 14px !important;
  background: linear-gradient(135deg, #22c55e, #16a34a) !important;
  box-shadow: 0 10px 24px rgba(34, 197, 94, 0.24);
  font-weight: 600;
}

.sidebar-section-title {
  margin: 6px 8px 10px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #94a3b8;
}

.dialog-list {
  flex: 1;
  overflow-y: auto;
  padding: 2px 4px 6px;
}

.dialog-item {
  padding: 14px 14px;
  margin-bottom: 10px;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.22s ease;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.72);
}

.dialog-item:hover {
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.96);
  border-color: rgba(34, 197, 94, 0.16);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.dialog-item.active {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.14), rgba(255, 255, 255, 0.96));
  border-color: rgba(34, 197, 94, 0.3);
  box-shadow: 0 12px 26px rgba(34, 197, 94, 0.12);
}

.dialog-item-title {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dialog-item-desc {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}

.user-info {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.72);
}

.user-avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ecfdf5;
  color: #16a34a;
  font-weight: 700;
  font-size: 16px;
}

.user-label {
  font-size: 12px;
  color: #94a3b8;
}

.username {
  margin-top: 2px;
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.logout-btn {
  height: 40px;
  border-radius: 12px !important;
}

/* =======================
   Main
======================= */
.chat-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: 18px 22px 18px 22px;
}

.chat-main-header {
  flex-shrink: 0;
  padding: 4px 8px 14px;
}

.header-title {
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
}

.header-subtitle {
  margin-top: 6px;
  font-size: 13px;
  color: #64748b;
}

.chat-messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.56);
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.65),
    0 14px 40px rgba(15, 23, 42, 0.06);
}

.messages-inner {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 24px 28px;
  box-sizing: border-box;
}

.chat-empty {
  min-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  padding: 80px 20px;
  text-align: center;
}

.empty-icon {
  font-size: 44px;
  margin-bottom: 14px;
}

.empty-title {
  font-size: 22px;
  font-weight: 700;
  color: #111827;
}

.empty-desc {
  margin-top: 10px;
  font-size: 14px;
  color: #6b7280;
}

.chat-input-shell {
  flex-shrink: 0;
  padding-top: 16px;
}

.chat-input-area {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 14px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.92);
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.08);
}

.chat-input {
  flex: 1;
}

.chat-input :deep(.el-textarea__inner) {
  min-height: 64px !important;
  max-height: 140px !important;
  padding: 16px 18px !important;
  border: 1px solid #dbe3ee !important;
  border-radius: 18px !important;
  box-shadow: none !important;
  background: #f8fafc !important;
  color: #111827;
  font-size: 14px;
  line-height: 1.7;
  resize: none !important;
  transition: all 0.2s ease;
}

.chat-input :deep(.el-textarea__inner:focus) {
  border-color: #22c55e !important;
  background: #ffffff !important;
  box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.12) !important;
}

.send-button {
  width: 52px !important;
  height: 52px !important;
  border: none !important;
  border-radius: 18px !important;
  flex-shrink: 0;
  background: linear-gradient(135deg, #22c55e, #16a34a) !important;
  box-shadow: 0 10px 24px rgba(34, 197, 94, 0.22);
}

.send-button:disabled {
  opacity: 0.65;
}

/* =======================
   Scrollbar
======================= */
.dialog-list::-webkit-scrollbar,
.chat-messages::-webkit-scrollbar {
  width: 8px;
}

.dialog-list::-webkit-scrollbar-thumb,
.chat-messages::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.35);
  border-radius: 999px;
}

.dialog-list::-webkit-scrollbar-track,
.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}

/* =======================
   Responsive
======================= */
@media (max-width: 960px) {
  .chat-sidebar {
    width: 240px;
  }

  .chat-main {
    padding: 14px;
  }

}

@media (max-width: 768px) {
  .chat-container {
    flex-direction: column;
  }

  .chat-sidebar {
    width: 100%;
    height: auto;
    border-right: none;
    border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  }

  .dialog-list {
    max-height: 180px;
  }

  .chat-main {
    padding: 12px;
  }

  .header-title {
    font-size: 20px;
  }

  .chat-input-area {
    border-radius: 18px;
    padding: 10px;
  }

  .send-button {
    width: 46px !important;
    height: 46px !important;
    border-radius: 14px !important;
  }
}

.evidence-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.evidence-card {
  padding: 14px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
}

.evidence-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.evidence-source {
  font-size: 13px;
  font-weight: 700;
  color: #16a34a;
}

.evidence-score {
  font-size: 12px;
  color: #64748b;
}

.evidence-title {
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.evidence-content {
  font-size: 13px;
  line-height: 1.7;
  color: #334155;
  white-space: pre-wrap;
  word-break: break-word;
}


.dialog-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.dialog-main {
  flex: 1;
  min-width: 0;
}

.delete-dialog-btn {
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.dialog-item:hover .delete-dialog-btn,
.dialog-item.active .delete-dialog-btn {
  opacity: 1;
}
</style>