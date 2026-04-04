<template>
  <div class="chat-container">
    <div class="chat-sidebar">
      <el-button 
        type="primary" 
        class="new-dialog-btn"
        @click="newDialog"
      >
        新建对话
      </el-button>
      
      <div class="dialog-list">
        <div 
          v-for="(dialog, index) in dialogs" 
          :key="index"
          class="dialog-item"
          :class="{ active: selectedIndex === index }"
          @click="switchDialog(index)"
        >
          {{ dialog.title }}
        </div>
      </div>
      
      <div class="user-info">
        <div>{{ userInfo?.username }}</div>
        <el-button 
          type="danger" 
          class="logout-btn"
          @click="handleLogout"
        >
          退出登录
        </el-button>
      </div>
    </div>
    
    <div class="chat-main">
      <div class="chat-messages">
        <ChatMessage 
          v-for="(message, index) in currentMessages" 
          :key="index"
          :message="message"
        />
      </div>
      
      <div class="chat-input-area">
        <el-input
          v-model="inputMessage"
          type="textarea"
          class="chat-input"
          placeholder="请输入消息..."
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
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useChatStream } from '@/composables/useChatStream'
import ChatMessage from '@/components/ChatMessage.vue'
import { ArrowRight } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

const inputMessage = ref('')

const dialogs = ref([
  { title: '第一次咨询', messages: [] }
])

const selectedIndex = ref(0)

const currentMessages = computed(() => {
  return dialogs.value[selectedIndex.value]?.messages || []
})

const userInfo = computed(() => {
  return userStore.userInfo
})

const { isGenerating, sendMessage: streamSendMessage } = useChatStream()

const newDialog = () => {
  dialogs.value.push({
    title: `对话 ${dialogs.value.length + 1}`,
    messages: []
  })
  selectedIndex.value = dialogs.value.length - 1
}

const switchDialog = (index) => {
  selectedIndex.value = index
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isGenerating.value) return

  const message = inputMessage.value.trim()
  inputMessage.value = ''

  try {
    await streamSendMessage(currentMessages.value, message)
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
</script>

<style scoped>
.dialog-list {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 20px;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chat-container {
  display: flex;
  height: 100vh;
  background-color: var(--light-gray);
}

.chat-sidebar {
  width: 280px;
  background-color: var(--white);
  padding: 20px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #eee;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.chat-input-area {
  padding: 20px;
  background-color: var(--white);
  border-top: 1px solid #eee;
  display: flex;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  resize: none;
  border: 1px solid #ddd;
  border-radius: var(--border-radius);
  padding: 12px;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.5;
  min-height: 60px;
  max-height: 120px;
  outline: none;
}

.chat-input:focus {
  border-color: var(--primary-green);
}

.send-button {
  background-color: var(--primary-green) !important;
  border-color: var(--primary-green) !important;
  color: white !important;
  border-radius: 50% !important;
  width: 40px !important;
  height: 40px !important;
  margin-left: 10px !important;
}
</style>