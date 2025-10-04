import { useState, useCallback, useRef, useEffect } from 'react'
import axios from 'axios'

export const useChat = (sessionId) => {
  const [messages, setMessages] = useState([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState(null)
  const [dashboardUpdates, setDashboardUpdates] = useState([])
  const eventSourceRef = useRef(null)

  // Load session history
  useEffect(() => {
    if (sessionId) {
      loadSession(sessionId)
    }
  }, [sessionId])

  const loadSession = async (sessionId) => {
    try {
      const response = await axios.get(`/api/v1/chat/sessions/${sessionId}`)
      setMessages(response.data.messages || [])
      setDashboardUpdates(response.data.dashboard_snapshots || [])
    } catch (err) {
      console.error('Failed to load session:', err)
      setError('Failed to load chat history')
    }
  }

  const sendMessage = useCallback(async (content, portfolioId = null) => {
    if (!sessionId || !content.trim()) return

    // Add user message immediately
    const userMessage = {
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMessage])
    setIsStreaming(true)
    setError(null)

    // Prepare assistant message placeholder
    let assistantContent = ''
    const assistantMessage = {
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      tool_calls: []
    }

    try {
      // Create EventSource for SSE streaming
      const url = `/api/v1/chat/sessions/${sessionId}/messages`
      const response = await axios.post(url,
        { content: content.trim(), portfolio_id: portfolioId },
        {
          headers: { 'Accept': 'text/event-stream' },
          responseType: 'stream',
          adapter: 'fetch'
        }
      )

      const reader = response.data.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            const eventType = line.substring(7).trim()
            continue
          }

          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.substring(6))

            if (data.content) {
              assistantContent += data.content
              setMessages(prev => {
                const updated = [...prev]
                const lastMsg = updated[updated.length - 1]
                if (lastMsg && lastMsg.role === 'assistant') {
                  lastMsg.content = assistantContent
                } else {
                  updated.push({ ...assistantMessage, content: assistantContent })
                }
                return updated
              })
            }

            if (data.tool_call) {
              assistantMessage.tool_calls.push(data.tool_call)
            }

            if (data.dashboard_update) {
              setDashboardUpdates(prev => [...prev, data.dashboard_update])
            }
          }
        }
      }

    } catch (err) {
      console.error('Chat error:', err)
      setError('Failed to send message')
    } finally {
      setIsStreaming(false)
    }
  }, [sessionId])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  return {
    messages,
    isStreaming,
    error,
    dashboardUpdates,
    sendMessage,
    clearError
  }
}
