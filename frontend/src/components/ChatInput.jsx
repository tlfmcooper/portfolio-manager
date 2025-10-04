import { useState } from 'react'
import { Box, TextField, IconButton, CircularProgress } from '@mui/material'
import { Send } from '@mui/icons-material'

const ChatInput = ({ onSend, isStreaming }) => {
  const [input, setInput] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (input.trim() && !isStreaming) {
      onSend(input)
      setInput('')
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <Box
      component="form"
      onSubmit={handleSubmit}
      sx={{
        display: 'flex',
        gap: 1,
        p: 2,
        borderTop: 1,
        borderColor: 'divider',
        backgroundColor: 'background.paper',
      }}
    >
      <TextField
        fullWidth
        multiline
        maxRows={4}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyPress={handleKeyPress}
        placeholder="Ask about your portfolio, simulations, or rebalancing..."
        disabled={isStreaming}
        variant="outlined"
        size="small"
      />
      <IconButton
        type="submit"
        color="primary"
        disabled={!input.trim() || isStreaming}
        sx={{ alignSelf: 'flex-end' }}
      >
        {isStreaming ? <CircularProgress size={24} /> : <Send />}
      </IconButton>
    </Box>
  )
}

export default ChatInput
