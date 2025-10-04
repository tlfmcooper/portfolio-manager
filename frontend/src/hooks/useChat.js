import { useState, useCallback, useRef, useEffect } from 'react';
import EventSource from 'eventsource';
import { chatAPI } from '../services/api';

export const useChat = (sessionId) => {
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(null);
  const [dashboardUpdate, setDashboardUpdate] = useState(null);
  const eventSourceRef = useRef(null);

  // Load session history
  useEffect(() => {
    if (sessionId) {
      loadSession();
    }
  }, [sessionId]);

  const loadSession = async () => {
    try {
      const response = await chatAPI.getSession(sessionId);
      setMessages(response.data.messages || []);
    } catch (err) {
      console.error('Failed to load session:', err);
      setError('Failed to load chat history');
    }
  };

  const sendMessage = useCallback(
    async (content, portfolioId = null) => {
      if (!sessionId || !content.trim()) return;

      // Add user message immediately
      const userMessage = {
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      setIsStreaming(true);
      setError(null);
      setDashboardUpdate(null);

      try {
        // Setup SSE connection
        const token = localStorage.getItem('token');
        const url = `${chatAPI.getStreamURL(sessionId)}`;

        const eventSource = new EventSource(url, {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        eventSourceRef.current = eventSource;

        let assistantMessage = {
          role: 'assistant',
          content: '',
          timestamp: new Date().toISOString(),
        };
        let messageAdded = false;

        eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            if (data.type === 'message_delta' && data.content) {
              // Append to assistant message
              assistantMessage.content += data.content;

              if (!messageAdded) {
                setMessages((prev) => [...prev, assistantMessage]);
                messageAdded = true;
              } else {
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1] = { ...assistantMessage };
                  return newMessages;
                });
              }
            } else if (data.type === 'tool_call') {
              // Tool call notification
              console.log('Tool call:', data.tool_call);
            } else if (data.type === 'dashboard_update') {
              // Dashboard update
              setDashboardUpdate(data.dashboard_update);
            } else if (data.type === 'done') {
              // Stream complete
              eventSource.close();
              setIsStreaming(false);
            } else if (data.type === 'error') {
              setError(data.content);
              eventSource.close();
              setIsStreaming(false);
            }
          } catch (err) {
            console.error('Error parsing SSE data:', err);
          }
        };

        eventSource.onerror = (err) => {
          console.error('SSE error:', err);
          setError('Connection error');
          eventSource.close();
          setIsStreaming(false);
        };

        // Send the actual message via POST
        await chatAPI.sendMessage(sessionId, { content, portfolio_id: portfolioId });
      } catch (err) {
        console.error('Error sending message:', err);
        setError(err.response?.data?.detail || 'Failed to send message');
        setIsStreaming(false);
      }
    },
    [sessionId]
  );

  const stopStreaming = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  return {
    messages,
    isStreaming,
    error,
    dashboardUpdate,
    sendMessage,
    stopStreaming,
  };
};
