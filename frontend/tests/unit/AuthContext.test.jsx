import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => {
  const api = {
    get: vi.fn(),
    post: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  };

  return {
    api,
    axios: {
      create: vi.fn(() => api),
      post: vi.fn(),
    },
  };
});

vi.mock('axios', () => ({
  default: mocks.axios,
}));

vi.mock('react-hot-toast', () => ({
  default: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

vi.mock('../../src/services/portfolioService', () => ({
  default: class MockPortfolioService {
    getPortfolio = vi.fn();
  },
}));

import { AuthProvider, useAuth } from '../../src/contexts/AuthContext';

const bootstrapUser = {
  id: 1,
  username: 'tester',
  email: 'tester@example.com',
  full_name: 'Test User',
  is_active: true,
  is_superuser: false,
  created_at: '2026-05-24T00:00:00Z',
  updated_at: '2026-05-24T00:00:00Z',
};

const Probe = () => {
  const auth = useAuth();

  return (
    <div>
      <span data-testid="loading">{String(auth.loading)}</span>
      <span data-testid="authenticated">{String(auth.isAuthenticated)}</span>
      <span data-testid="user">{auth.user?.username || 'none'}</span>
      <span data-testid="portfolio">{auth.portfolioId || 'none'}</span>
      <span data-testid="onboarded">{String(auth.isOnboarded)}</span>
      <span data-testid="error">{auth.error || 'none'}</span>
    </div>
  );
};

const renderAuth = () => render(
  <MemoryRouter>
    <AuthProvider>
      <Probe />
    </AuthProvider>
  </MemoryRouter>
);

describe('AuthProvider bootstrap', () => {
  beforeEach(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    mocks.api.get.mockReset();
    mocks.api.post.mockReset();
    mocks.axios.post.mockReset();
  });

  it('loads authenticated user and portfolio from the lightweight bootstrap endpoint', async () => {
    localStorage.setItem('access_token', 'token');
    mocks.api.get.mockResolvedValue({
      data: {
        user: bootstrapUser,
        portfolio_id: 42,
        is_onboarded: true,
      },
    });

    renderAuth();

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));
    expect(mocks.api.get).toHaveBeenCalledWith('/auth/bootstrap', { timeout: 15000 });
    expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
    expect(screen.getByTestId('user')).toHaveTextContent('tester');
    expect(screen.getByTestId('portfolio')).toHaveTextContent('42');
    expect(screen.getByTestId('onboarded')).toHaveTextContent('true');
  });

  it('clears stored tokens on a 401 bootstrap response', async () => {
    localStorage.setItem('access_token', 'expired');
    localStorage.setItem('refresh_token', 'refresh');
    mocks.api.get.mockRejectedValue({ response: { status: 401 } });

    renderAuth();

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
    expect(screen.getByTestId('authenticated')).toHaveTextContent('false');
    expect(screen.getByTestId('user')).toHaveTextContent('none');
  });

  it('keeps the token and exposes a recoverable error on network failure', async () => {
    localStorage.setItem('access_token', 'token');
    mocks.api.get.mockRejectedValue({ code: 'ERR_NETWORK' });

    renderAuth();

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));
    expect(localStorage.getItem('access_token')).toBe('token');
    expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
    expect(screen.getByTestId('user')).toHaveTextContent('none');
    expect(screen.getByTestId('error')).toHaveTextContent('could not reach the server');
  });

  it('marks authenticated users without a portfolio as not onboarded', async () => {
    localStorage.setItem('access_token', 'token');
    mocks.api.get.mockResolvedValue({
      data: {
        user: bootstrapUser,
        portfolio_id: null,
        is_onboarded: false,
      },
    });

    renderAuth();

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));
    expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
    expect(screen.getByTestId('portfolio')).toHaveTextContent('none');
    expect(screen.getByTestId('onboarded')).toHaveTextContent('false');
  });
});
