import { Box, Paper, Typography, Chip } from '@mui/material'
import { format } from 'date-fns'
import { Person, SmartToy } from '@mui/icons-material'

const ChatMessage = ({ message }) => {
  const isUser = message.role === 'user'

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        mb: 2,
      }}
    >
      <Paper
        elevation={1}
        sx={{
          maxWidth: '70%',
          p: 2,
          backgroundColor: isUser ? 'primary.light' : 'grey.100',
          color: isUser ? 'primary.contrastText' : 'text.primary',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          {isUser ? <Person sx={{ mr: 1, fontSize: 20 }} /> : <SmartToy sx={{ mr: 1, fontSize: 20 }} />}
          <Typography variant="caption">
            {isUser ? 'You' : 'AI Assistant'}
          </Typography>
          <Typography variant="caption" sx={{ ml: 'auto', opacity: 0.7 }}>
            {message.timestamp && format(new Date(message.timestamp), 'HH:mm')}
          </Typography>
        </Box>

        <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
          {message.content}
        </Typography>

        {message.tool_calls && message.tool_calls.length > 0 && (
          <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
            {message.tool_calls.map((tool, idx) => (
              <Chip
                key={idx}
                label={tool.name}
                size="small"
                variant="outlined"
                sx={{ fontSize: '0.75rem' }}
              />
            ))}
          </Box>
        )}
      </Paper>
    </Box>
  )
}

export default ChatMessage
