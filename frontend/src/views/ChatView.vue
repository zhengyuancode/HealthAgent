<template>
  <div class="chat-container">
    <!-- 左侧边栏 -->
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
    
    <!-- 右侧主内容区 -->
    <div class="chat-main">
      <!-- 消息列表 -->
      <div class="chat-messages">
        <ChatMessage 
          v-for="(message, index) in currentMessages" 
          :key="index"
          :message="message"
        />
      </div>
      
      <!-- 输入区 -->
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
          :disabled="isSending"
          @click="sendMessage"
        >
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useChatStream } from '@/composables/useChatStream'
import ChatMessage from '@/components/ChatMessage.vue'
import { ArrowRight } from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()

const inputMessage = ref('')
const isSending = ref(false)

// 对话列表
const dialogs = ref([
  { title: '第一次咨询', messages: [] }
])

// 当前选中的对话索引
const selectedIndex = ref(0)

// 获取当前对话的消息列表
const currentMessages = computed(() => {
  return dialogs.value[selectedIndex.value]?.messages || []
})

// 获取用户信息
const userInfo = computed(() => {
  return userStore.userInfo
})

// 初始化聊天流
const { messages, isGenerating, sendMessage: streamSendMessage } = useChatStream()

// 监听聊天消息变化并更新当前对话
const updateCurrentDialog = () => {
  if (dialogs.value[selectedIndex.value]) {
    dialogs.value[selectedIndex.value].messages = [...messages.value]
  }
}

// 新建对话
const newDialog = () => {
  const newDialog = {
    title: `对话 ${dialogs.value.length + 1}`,
    messages: []
  }
  dialogs.value.push(newDialog)
  selectedIndex.value = dialogs.value.length - 1
}

// 切换对话
const switchDialog = (index) => {
  selectedIndex.value = index
}

// 发送消息
const sendMessage = async () => {
  if (!inputMessage.value.trim() || isSending.value) return
  
  isSending.value = true
  const message = inputMessage.value.trim()
  inputMessage.value = ''
  
  try {
    await streamSendMessage(message)
  } catch (error) {
    console.error('发送消息失败:', error)
  } finally {
    isSending.value = false
  }
}

// 处理键盘事件
const handleKeyDown = (event) => {
  if (event.key === 'Enter') {
    if (event.ctrlKey || event.metaKey) {
      // Ctrl+Enter 换行
      inputMessage.value += '\n'
    } else {
      // Enter 发送
      event.preventDefault()
      sendMessage()
    }
  }
}

// 退出登录
const handleLogout = () => {
  userStore.clearToken()
  router.push('/login')
}

// 监听聊天消息变化
onMounted(() => {
  // 监听消息变化
  const interval = setInterval(() => {
    updateCurrentDialog()
  }, 100)
  
  return () => clearInterval(interval)
})
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