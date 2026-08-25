import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../../src/contexts/AuthContext', () => ({
  useAuth: () => ({ api: { post: vi.fn() } }),
}));

import BuyAssetForm from '../../src/components/forms/BuyAssetForm';

describe('BuyAssetForm', () => {
  it('makes unit pricing explicit and previews the transaction total', () => {
    render(<BuyAssetForm />);

    expect(screen.getByLabelText(/price per share \/ unit/i)).toBeInTheDocument();
    expect(screen.getByText(/enter the unit price, not the transaction total/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/^quantity$/i), { target: { value: '20' } });
    fireEvent.change(screen.getByLabelText(/price per share \/ unit/i), {
      target: { value: '18.79' },
    });

    expect(screen.getByText('20 × $18.79 = $375.80')).toBeInTheDocument();
  });
});
