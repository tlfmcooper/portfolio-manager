import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Chat from '../pages/Chat'
import { AuthProvider } from '../contexts/AuthContext'

// Mock axios
jest.mock('axios')

const renderChat = () => {
  return render(
    <BrowserRouter>
      <AuthProvider>
        <Chat />
      </AuthProvider>
    </BrowserRouter>
  )
}

describe('Chat Component', () => {
  test('renders chat interface', () => {
    renderChat()
    expect(screen.getByText(/AI Portfolio Assistant/i)).toBeInTheDocument()
  })

  test('displays welcome message when no messages', () => {
    renderChat()
    expect(screen.getByText(/Welcome to your AI Portfolio Assistant/i)).toBeInTheDocument()
  })

  test('renders portfolio selector', () => {
    renderChat()
    expect(screen.getByLabelText(/Portfolio/i)).toBeInTheDocument()
  })

  test('renders chat input', () => {
    renderChat()
    const input = screen.getByPlaceholderText(/Ask about your portfolio/i)
    expect(input).toBeInTheDocument()
  })

  test('allows typing in chat input', () => {
    renderChat()
    const input = screen.getByPlaceholderText(/Ask about your portfolio/i)

    fireEvent.change(input, { target: { value: 'What is my portfolio value?' } })
    expect(input.value).toBe('What is my portfolio value?')
  })
})
