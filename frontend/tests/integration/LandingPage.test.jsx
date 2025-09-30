import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter as Router } from 'react-router-dom';
import LandingPage from '../../src/pages/LandingPage';

describe('LandingPage Integration', () => {
  it('renders all major sections and components', () => {
    render(
      <Router>
        <LandingPage />
      </Router>
    );

    // Check for Logo
    expect(screen.getByText('InvestSmart')).toBeInTheDocument();

    // Check for Navigation Menu items
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Risk Analytics')).toBeInTheDocument();
    expect(screen.getByText('Asset Allocation')).toBeInTheDocument();

    // Check for Action Buttons
    expect(screen.getByText('Log In')).toBeInTheDocument();
    expect(screen.getByText('Sign Up')).toBeInTheDocument();

    // Check for Hero Section content
    expect(screen.getByText('Manage Your Investments with Precision')).toBeInTheDocument();
    expect(screen.getByText('Get Started')).toBeInTheDocument();
    expect(screen.getByText('Learn More')).toBeInTheDocument();

    // Check for Key Features Section content
    expect(screen.getByText('Key Features')).toBeInTheDocument();
    expect(screen.getByText(
      /InvestSmart is the ultimate portfolio management solution/
    )).toBeInTheDocument();
  });

  it('navigation links and action buttons have correct href attributes', () => {
    render(
      <Router>
        <LandingPage />
      </Router>
    );

    // Navigation Links
    expect(screen.getByText('Overview')).toHaveAttribute('href', '/dashboard/Overview');
    expect(screen.getByText('Risk Analytics')).toHaveAttribute('href', '/dashboard/analytics');
    expect(screen.getByText('Asset Allocation')).toHaveAttribute('href', '/dashboard/portfolio');

    // Action Buttons
    expect(screen.getByText('Log In')).toHaveAttribute('href', '/login');
    expect(screen.getByText('Sign Up')).toHaveAttribute('href', '/register');

    // Hero Section CTA Buttons
    expect(screen.getByText('Get Started')).toHaveAttribute('href', '/#get-started');
    expect(screen.getByText('Learn More')).toHaveAttribute('href', '/#learn-more');
  });
});
