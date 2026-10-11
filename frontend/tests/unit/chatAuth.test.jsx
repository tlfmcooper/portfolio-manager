import React from 'react';
import { act, cleanup, render, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { createChatClient } from '../../src/services/chatClient';

const mocks = vi.hoisted(() => ({ fetch: vi.fn(), refresh: vi.fn(), api: null }));
vi.mock('axios', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, default: { ...actual.default,
    post: (...args) => mocks.refresh(...args),
    create: config => {
      const api = actual.default.create(config);
      api.defaults.adapter = async config => ({ data: { user: { id: 1 }, portfolio_id: 7, is_onboarded: true }, status: 200, headers: {}, config });
      api.defaults.env.fetch = (...args) => mocks.fetch(...args);
      mocks.api = api;
      return api;
    },
  } };
});
import { AuthProvider } from '../../src/contexts/AuthContext';

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem('access_token', 'expired');
  localStorage.setItem('refresh_token', 'refresh');
  mocks.fetch.mockReset();
  mocks.refresh.mockReset();
});
afterEach(cleanup);

it('refreshes an expired JWT before consuming chat output and preserves the request body', async () => {
  const requests = [];
  mocks.fetch.mockImplementation(async request => {
    requests.push({ authorization: request.headers.get('Authorization'), body: await request.text() });
    if (requests.length === 1) return new Response('{"detail":"expired"}', { status: 401 });
    return new Response('data: {"candidates":[{"content":{"parts":[{"text":"Hello"}]}}]}\n\ndata: {"done":true}\n\n', { status: 200, headers: { 'Content-Type': 'text/event-stream' } });
  });
  mocks.refresh.mockResolvedValue({ data: { access_token: 'fresh', refresh_token: 'new-refresh' } });
  await act(async () => { render(<MemoryRouter><AuthProvider><span>Ready</span></AuthProvider></MemoryRouter>); });
  await waitFor(() => expect(mocks.api).toBeTruthy());
  const chat = createChatClient(mocks.api, { systemInstruction: 'Helpful', tools: [] }).startChat();
  const result = await chat.sendMessage([{ text: 'Hello' }]);
  expect(result.response.text()).toBe('Hello');
  expect(requests.map(request => request.authorization)).toEqual(['Bearer expired', 'Bearer fresh']);
  expect(requests[0].body).toBe(requests[1].body);
  expect(mocks.refresh).toHaveBeenCalledTimes(1);
  expect(localStorage.getItem('access_token')).toBe('fresh');
});

it('never replays a request after a stream starts and is interrupted', async () => {
  mocks.fetch.mockResolvedValue(new Response('data: {"candidates":[{"content":{"parts":[{"text":"partial"}]}}]}\n\n', { status: 200 }));
  await act(async () => { render(<MemoryRouter><AuthProvider><span>Ready</span></AuthProvider></MemoryRouter>); });
  const chat = createChatClient(mocks.api, { systemInstruction: 'Helpful', tools: [] }).startChat();
  await expect(chat.sendMessage([{ text: 'Hello' }])).rejects.toThrow('interrupted');
  expect(mocks.fetch).toHaveBeenCalledTimes(1);
  expect(mocks.refresh).not.toHaveBeenCalled();
});
