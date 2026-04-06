import request from '@/utils/request'

export function createChatSession(data) {
  return request.post('/chat/sessions', data)
}

export function getChatSessions() {
  return request.get('/chat/sessions')
}

export function getChatMessages(sessionId) {
  return request.get(`/chat/sessions/${sessionId}/messages`)
}

export function deleteChatSession(sessionId) {
  return request.delete(`/chat/sessions/${sessionId}`)
}