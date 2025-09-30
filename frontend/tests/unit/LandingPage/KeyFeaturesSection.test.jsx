import React from 'react';
import { render, screen } from '@testing-library/react';
import KeyFeaturesSection from '../../../src/components/LandingPage/KeyFeaturesSection';

describe('KeyFeaturesSection', () => {
  it('renders the section title', () => {
    render(<KeyFeaturesSection />);
    expect(screen.getByText('Key Features')).toBeInTheDocument();
  });

  it('renders the section subtitle', () => {
    render(<KeyFeaturesSection />);
    expect(screen.getByText(
      /InvestSmart is the ultimate portfolio management solution/
    )).toBeInTheDocument();
  });

  it('renders placeholder feature items', () => {
    render(<KeyFeaturesSection />);
    expect(screen.getByText('Feature 1')).toBeInTheDocument();
    expect(screen.getByText('Feature 2')).toBeInTheDocument();
    expect(screen.getByText('Feature 3')).toBeInTheDocument();
  });
});
