import React, { useState } from 'react';
import { Box, TextField, IconButton, CircularProgress } from '@mui/material';
import { Send, Stop } from '@mui/icons-material';

const ChatInput = ({ onSend, isStreaming, onStop }) => {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isStreaming) {
      onSend(input);
      setInput('');
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', gap: 1 }}>
      <TextField
        fullWidth
        multiline
        maxRows={4}
        placeholder="Ask about your portfolio..."
        value={input}
        onChange={(e) => setInput(e.target.value)}
        disabled={isStreaming}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
          }
        }}
      />
      {isStreaming ? (
        <IconButton onClick={onStop} color="error">
          <Stop />
        </IconButton>
      ) : (
        <IconButton
          type="submit"
          color="primary"
          disabled={!input.trim() || isStreaming}
        >
          {isStreaming ? <CircularProgress size={24} /> : <Send />}
        </IconButton>
      )}
    </Box>
  );
};

export default ChatInput;
