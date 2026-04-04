import { ref } from 'vue'

export function useChatStream() {
  const isGenerating = ref(false)

  const sendMessage = async (targetMessages, content) => {
    const token = localStorage.getItem('token')

    const userMessage = {
      role: 'user',
      content
    }

    const assistantMessage = {
      role: 'assistant',
      content: '',
      thinking: '',
      showThinking: true,
      loading: true,
      meta: null
    }

    targetMessages.push(userMessage)
    targetMessages.push(assistantMessage)

    isGenerating.value = true

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ query: content })
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      if (!response.body) {
        throw new Error('浏览器不支持流式读取')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        const blocks = buffer.split('\n\n')
        buffer = blocks.pop() || ''

        for (const block of blocks) {
          const dataLine = block
            .split('\n')
            .find(line => line.startsWith('data: '))

          if (!dataLine) continue

          const payload = JSON.parse(dataLine.slice(6))
          const { type, data } = payload

          switch (type) {
            case 'status':
              assistantMessage.showThinking = true
              assistantMessage.thinking += `${data.message}\n`
              break

            case 'thinking':
              assistantMessage.showThinking = true
              assistantMessage.thinking += data.delta
              break

            case 'answer':
              // 正式回答开始后隐藏思考区
              assistantMessage.showThinking = false
              assistantMessage.content += data.delta
              break

            case 'done':
              assistantMessage.showThinking = false
              assistantMessage.loading = false
              assistantMessage.meta = data.final_response
              if (!assistantMessage.content && data.final_response?.answer) {
                assistantMessage.content = data.final_response.answer
              }
              break

            case 'error':
              assistantMessage.showThinking = false
              assistantMessage.loading = false
              assistantMessage.content = data.message || '生成失败'
              break

            default:
              break
          }
        }
      }

      assistantMessage.loading = false
    } catch (error) {
      assistantMessage.showThinking = false
      assistantMessage.loading = false
      assistantMessage.content = `发送失败：${error.message}`
      throw error
    } finally {
      isGenerating.value = false
    }
  }

  return {
    isGenerating,
    sendMessage
  }
}