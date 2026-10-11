import React from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  auth: { user: { id: 1 }, portfolioId: 7, api: { get: vi.fn(), put: vi.fn(), delete: vi.fn(), post: vi.fn() } },
  execute: vi.fn(),
  capture: vi.fn(),
}));
vi.mock('../../src/contexts/AuthContext', () => ({ useAuth: () => mocks.auth }));
vi.mock('../../src/contexts/AgentContext', () => ({ useAgentContext: () => ({ resetAllParams: vi.fn() }) }));
vi.mock('../../src/contexts/PortfolioScenarioContext', () => ({ usePortfolioScenario: () => null }));
vi.mock('../../src/tools/agentTools', () => ({ tools: [], executeTool: (...args) => mocks.execute(...args) }));
vi.mock('html2canvas', () => ({ default: (...args) => mocks.capture(...args) }));
import PortfolioChatWidget from '../../src/components/PortfolioChatWidget';

const mount = async () => {
  let view;
  await act(async () => { view = render(<MemoryRouter><PortfolioChatWidget /></MemoryRouter>); });
  return view;
};
const open = () => fireEvent.click(screen.getByRole('button', { name: 'Portfolio Pilot' }));
const settings = () => fireEvent.click(screen.getByRole('button', { name: 'Chat settings' }));
const defer = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
function response(parts) {
  return { data: new ReadableStream({ start(controller) {
    controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify({ candidates: [{ content: { parts } }] })}\n\ndata: {"done":true}\n\n`));
    controller.close();
  } }) };
}

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
  mocks.auth.user = { id: 1 };
  mocks.auth.api.get.mockResolvedValue({ data: { configured: false } });
  mocks.auth.api.put.mockResolvedValue({ data: { configured: true } });
  mocks.auth.api.delete.mockResolvedValue({ data: { configured: false } });
  mocks.capture.mockResolvedValue({ toDataURL: () => 'data:image/jpeg;base64,screenshot-data' });
  Element.prototype.scrollIntoView = vi.fn();
});
afterEach(cleanup);

describe('chat key settings', () => {
  it('discards the legacy key, saves only to the API, clears the draft, and restores status on reload', async () => {
    localStorage.setItem('gemini_api_key', 'old-secret');
    const view = await mount();
    open(); settings();
    await waitFor(() => expect(screen.getByLabelText('Gemini API Key')).toBeEnabled());
    expect(localStorage.getItem('gemini_api_key')).toBeNull();
    expect(screen.getByLabelText('Gemini API Key')).toHaveValue('');
    fireEvent.change(screen.getByLabelText('Gemini API Key'), { target: { value: 'new-secret' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save Key' }));
    await waitFor(() => expect(screen.queryByLabelText('Gemini API Key')).not.toBeInTheDocument());
    expect(mocks.auth.api.put).toHaveBeenCalledWith('/chat/api-key', { api_key: 'new-secret' }, expect.objectContaining({ signal: expect.any(AbortSignal) }));
    settings();
    expect(screen.getByLabelText('Gemini API Key')).toHaveValue('');
    expect(screen.getByText('Key saved securely to your account.')).toBeInTheDocument();
    expect(JSON.stringify(localStorage)).not.toContain('new-secret');
    view.unmount();
    mocks.auth.api.get.mockResolvedValue({ data: { configured: true } });
    await mount(); open(); settings();
    await screen.findByText('Key saved securely to your account.');
    expect(screen.getByLabelText('Gemini API Key')).toHaveValue('');
  });

  it('shows failed saves without marking the key configured or exposing server diagnostics', async () => {
    mocks.auth.api.put.mockRejectedValue(new Error('private provider details'));
    await mount(); open(); settings();
    await waitFor(() => expect(screen.getByLabelText('Gemini API Key')).toBeEnabled());
    fireEvent.change(screen.getByLabelText('Gemini API Key'), { target: { value: 'draft-secret' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save Key' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be saved');
    expect(screen.getByLabelText('Gemini API Key')).toHaveValue('draft-secret');
    expect(screen.queryByText('Key saved securely to your account.')).not.toBeInTheDocument();
    expect(screen.queryByText('private provider details')).not.toBeInTheDocument();
  });

  it('removes a saved key and prompts for a replacement', async () => {
    mocks.auth.api.get.mockResolvedValue({ data: { configured: true } });
    await mount(); open(); settings();
    await screen.findByRole('button', { name: 'Remove Key' });
    fireEvent.click(screen.getByRole('button', { name: 'Remove Key' }));
    await screen.findByText('Save your key to your account to enable chat.');
    expect(mocks.auth.api.delete).toHaveBeenCalledWith('/chat/api-key', expect.any(Object));
  });

  it('aborts account operations and ignores a stale status response when switching users', async () => {
    const pending = defer();
    mocks.auth.api.get.mockReturnValueOnce(pending.promise).mockResolvedValueOnce({ data: { configured: false } });
    const view = await mount(); open(); settings();
    const signal = mocks.auth.api.get.mock.calls[0][1].signal;
    mocks.auth.user = { id: 2 };
    await act(async () => view.rerender(<MemoryRouter><PortfolioChatWidget /></MemoryRouter>));
    expect(signal.aborted).toBe(true);
    await act(async () => pending.resolve({ data: { configured: true } }));
    settings();
    expect(screen.getByText('Save your key to your account to enable chat.')).toBeInTheDocument();
    expect(screen.getByLabelText('Gemini API Key')).toHaveValue('');
  });

  it('sends screenshots and tool follow-ups through the API and displays result cards', async () => {
    mocks.auth.api.get.mockResolvedValue({ data: { configured: true } });
    mocks.auth.api.post.mockResolvedValueOnce(response([{ functionCall: { name: 'get_portfolio_summary', args: {} }, thoughtSignature: 'signature' }]))
      .mockResolvedValueOnce(response([{ text: 'Your balance is $42.' }]));
    mocks.execute.mockResolvedValue('{"balance":42}');
    await mount(); open();
    fireEvent.change(screen.getByPlaceholderText('Ask anything...'), { target: { value: 'Show my chart' } });
    const form = screen.getByPlaceholderText('Ask anything...').closest('form');
    await waitFor(() => expect(form.querySelector('button')).toBeEnabled());
    fireEvent.submit(form);
    await screen.findByText('Your balance is $42.');
    expect(mocks.capture).toHaveBeenCalled();
    const first = mocks.auth.api.post.mock.calls[0][1];
    expect(first.contents.at(-1).parts[1].inlineData.data).toBe('screenshot-data');
    expect(mocks.auth.api.post).toHaveBeenCalledTimes(2);
    expect(screen.getByText('Balance')).toBeInTheDocument();
  });
});
