import { ref } from 'vue'

export function useChatStream(apiUrl = '/api/chat/stream') {
  const messages = ref([])
  const isGenerating = ref(false)
  
  const sendMessage = async (content) => {
    // 添加用户消息
    const userMessage = {
      role: 'user',
      content: content,
      timestamp: Date.now()
    }
    messages.value.push(userMessage)
    
    // 添加AI消息占位符
    const aiMessage = {
      role: 'assistant',
      content: '',
      timestamp: Date.now()
    }
    messages.value.push(aiMessage)
    
    isGenerating.value = true
    
    try {
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          message: content
        })
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) {
          break
        }
        
        const chunk = decoder.decode(value)
        // 处理流式数据块
        const lines = chunk.split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.substring(6)
            if (data.trim() !== '[DONE]') {
              // 更新最后一条AI消息的内容
              const lastMessage = messages.value[messages.value.length - 1]
              if (lastMessage.role === 'assistant') {
                lastMessage.content += data
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Error in chat stream:', error)
      // 移除AI消息占位符
      messages.value.pop()
      // 添加错误消息
      messages.value.push({
        role: 'assistant',
        content: '抱歉，发生了一个错误。请稍后再试。',
        timestamp: Date.now()
      })
    } finally {
      isGenerating.value = false
    }
  }
  
  const clearHistory = () => {
    messages.value = []
  }
  
  return {
    messages,
    isGenerating,
    sendMessage,
    clearHistory
  }
}