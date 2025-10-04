import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  Alert,
  CircularProgress,
  Button,
} from '@mui/material';
import { Add } from '@mui/icons-material';
import ChatMessage from '../components/ChatMessage';
import ChatInput from '../components/ChatInput';
import DashboardPreview from '../components/DashboardPreview';
import { useChat } from '../hooks/useChat';
import { chatAPI } from '../services/api';

const Chat = () => {
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [createError, setCreateError] = useState(null);
  const messagesEndRef = useRef(null);

  const { messages, isStreaming, error, dashboardUpdate, sendMessage, stopStreaming } =
    useChat(sessionId);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Create session on mount
  useEffect(() => {
    createSession();
  }, []);

  const createSession = async () => {
    setLoading(true);
    setCreateError(null);

    try {
      const response = await chatAPI.createSession({});
      setSessionId(response.data.session_id);
    } catch (err) {
      console.error('Failed to create session:', err);
      setCreateError(err.response?.data?.detail || 'Failed to create chat session');
    } finally {
      setLoading(false);
    }
  };

  const handleNewSession = async () => {
    await createSession();
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  if (createError) {
    return (
      <Box>
        <Alert severity="error" sx={{ mb: 2 }}>
          {createError}
        </Alert>
        <Button variant="contained" onClick={handleNewSession}>
          Try Again
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ height: 'calc(100vh - 120px)', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4">AI Portfolio Assistant</Typography>
        <Button
          startIcon={<Add />}
          variant="outlined"
          onClick={handleNewSession}
          disabled={isStreaming}
        >
          New Chat
        </Button>
      </Box>

      {/* Messages Area */}
      <Paper
        sx={{
          flex: 1,
          mb: 2,
          p: 2,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {messages.length === 0 ? (
          <Box
            sx={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              alignItems: 'center',
              color: 'text.secondary',
            }}
          >
            <Typography variant="h5" gutterBottom>
              Welcome to your AI Portfolio Assistant
            </Typography>
            <Typography variant="body1" textAlign="center" sx={{ maxWidth: 600 }}>
              Ask me anything about your portfolio, request rebalancing simulations,
              risk analysis, or optimization suggestions.
            </Typography>
            <Box sx={{ mt: 3 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Try asking:
              </Typography>
              <ul style={{ textAlign: 'left', color: 'inherit' }}>
                <li>"What are my portfolio's risk metrics?"</li>
                <li>"What would happen if I increased AAPL by 10%?"</li>
                <li>"Run a Monte Carlo simulation for my portfolio"</li>
                <li>"Show me the efficient frontier"</li>
              </ul>
            </Box>
          </Box>
        ) : (
          <>
            {messages.map((message, index) => (
              <ChatMessage key={index} message={message} />
            ))}
            {dashboardUpdate && <DashboardPreview dashboardUpdate={dashboardUpdate} />}
            {error && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {error}
              </Alert>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </Paper>

      {/* Input Area */}
      <Box>
        <ChatInput onSend={sendMessage} isStreaming={isStreaming} onStop={stopStreaming} />
      </Box>
    </Box>
  );
};

export default Chat;
