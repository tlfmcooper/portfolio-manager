import { useState, useEffect, useRef } from 'react'
import {
  Box,
  Container,
  Paper,
  Typography,
  Alert,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material'
import axios from 'axios'
import { useAuth } from '../contexts/AuthContext'
import { useChat } from '../hooks/useChat'
import ChatMessage from '../components/ChatMessage'
import ChatInput from '../components/ChatInput'
import DashboardPreview from '../components/DashboardPreview'

const Chat = () => {
  const { user } = useAuth()
  const [sessionId, setSessionId] = useState(null)
  const [portfolioId, setPortfolioId] = useState(1) // Default portfolio
  const messagesEndRef = useRef(null)

  const { messages, isStreaming, error, dashboardUpdates, sendMessage, clearError } = useChat(sessionId)

  // Initialize chat session on mount
  useEffect(() => {
    const initSession = async () => {
      try {
        const response = await axios.post('/api/v1/chat/sessions', {
          user_id: user?.id || 1,
        })
        setSessionId(response.data.session_id)
      } catch (err) {
        console.error('Failed to create session:', err)
      }
    }

    if (user) {
      initSession()
    }
  }, [user])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSendMessage = (content) => {
    sendMessage(content, portfolioId)
  }

  return (
    <Container maxWidth="lg" sx={{ height: 'calc(100vh - 100px)', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1">
          AI Portfolio Assistant
        </Typography>
        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel>Portfolio</InputLabel>
          <Select
            value={portfolioId}
            label="Portfolio"
            onChange={(e) => setPortfolioId(e.target.value)}
            size="small"
          >
            <MenuItem value={1}>Tech Portfolio</MenuItem>
            <MenuItem value={2}>Balanced Portfolio</MenuItem>
            <MenuItem value={3}>Growth Portfolio</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {error && (
        <Alert severity="error" onClose={clearError} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Paper
        elevation={3}
        sx={{
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <Box
          sx={{
            flexGrow: 1,
            overflowY: 'auto',
            p: 2,
            backgroundColor: 'grey.50',
          }}
        >
          {messages.length === 0 && !isStreaming && (
            <Box sx={{ textAlign: 'center', mt: 4 }}>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                👋 Welcome to your AI Portfolio Assistant
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Ask me anything about your portfolio, risk metrics, or rebalancing scenarios!
              </Typography>
              <Box sx={{ mt: 3, display: 'flex', flexDirection: 'column', gap: 1, alignItems: 'center' }}>
                <Typography variant="caption" color="text.secondary">
                  Try asking:
                </Typography>
                <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                  "What are my current portfolio metrics?"
                </Typography>
                <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                  "What if I decrease AAPL by 10% and increase QBTS by 50%?"
                </Typography>
                <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                  "Show me the efficient frontier"
                </Typography>
              </Box>
            </Box>
          )}

          {messages.map((message, index) => (
            <Box key={index}>
              <ChatMessage message={message} />
              {/* Show dashboard preview after assistant messages if available */}
              {message.role === 'assistant' &&
                dashboardUpdates
                  .filter((update) => update.timestamp >= message.timestamp)
                  .slice(-1)
                  .map((update, idx) => (
                    <DashboardPreview key={idx} update={update} />
                  ))}
            </Box>
          ))}

          <div ref={messagesEndRef} />
        </Box>

        <ChatInput onSend={handleSendMessage} isStreaming={isStreaming} />
      </Paper>
    </Container>
  )
}

export default Chat
