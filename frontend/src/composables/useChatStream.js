import { ref, reactive } from 'vue'

export function useChatStream(apiUrl = '/api/chat/stream') {
  const isGenerating = ref(false)

  const normalizeEvidence = (list = []) => {
    return list.flatMap((group, groupIndex) => {
      const evidenceList = Array.isArray(group?.evidence) ? group.evidence : []

      return evidenceList.map((item, evidenceIndex) => ({
        id: `${groupIndex}-${evidenceIndex}`,
        source: item.source || '未知来源',
        title: item.title || '',
        content:
          typeof item.content === 'string'
            ? item.content
            : JSON.stringify(item.content, null, 2),
        score: item.score,
        summary: group?.summary || '',
        task: group?.task || null
      }))
    })
  }

  const sendMessage = async (sessionId, messageList, content) => {
    const text = String(content || '').trim()
    if (!text || isGenerating.value) return

    messageList.push({
      role: 'user',
      content: text,
      timestamp: Date.now()
    })

    const aiMessage = reactive({
      role: 'assistant',
      content: '',
      thinking: '',
      showThinking: true,
      loading: true,
      evidence: [],
      evidenceReady: false,
      timestamp: Date.now()
    })

    messageList.push(aiMessage)

    isGenerating.value = true

    try {
      const token = localStorage.getItem('token')

      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          session_id: sessionId,
          query: text
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      if (!response.body) {
        throw new Error('响应体为空')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        const events = buffer.split('\n\n')
        buffer = events.pop() || ''

        for (const eventText of events) {
          const line = eventText.trim()
          if (!line.startsWith('data: ')) continue

          const raw = line.slice(6).trim()
          if (!raw) continue

          try {
            const event = JSON.parse(raw)

            switch (event.type) {
              case 'answer':
                aiMessage.content += event.data?.delta || event.delta || ''
                break

              case 'thinking':
                aiMessage.thinking += event.data?.delta || event.delta || ''
                break

              case 'status':
                aiMessage.thinking += event.data?.message || event.message || ''
                aiMessage.thinking += '\n'
                break

              case 'plan':
                aiMessage.thinking += event.data?.message || event.message || ''
                aiMessage.thinking += '\n'
                break

              case 'done':
                aiMessage.loading = false
                aiMessage.showThinking = false
                aiMessage.evidence = normalizeEvidence(event.data.final_response.graph_results).concat(
                  normalizeEvidence(event.data.final_response.rag_results)
                )
                aiMessage.evidenceReady = true
                console.log(normalizeEvidence(event.data.final_response.graph_results))
                console.log(normalizeEvidence(event.data.final_response.rag_results))
                break

              case 'error':
                aiMessage.loading = false
                aiMessage.showThinking = false
                aiMessage.content += `\n[错误] ${event.data?.message || '未知错误'}`
                break

              default:
                console.log('未知事件:', event)
            }
          } catch (err) {
            console.error('SSE JSON 解析失败:', raw, err)
          }
        }
      }
    } catch (error) {
      console.error('Error in chat stream:', error)
      aiMessage.content = '抱歉，发生了错误，请稍后再试。'
    } finally {
      aiMessage.loading = false
      isGenerating.value = false
    }
  }

  return {
    isGenerating,
    sendMessage
  }
}