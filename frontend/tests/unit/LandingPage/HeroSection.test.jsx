import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter as Router } from 'react-router-dom';
import HeroSection from '../../../src/components/LandingPage/HeroSection';

describe('HeroSection', () => {
  it('renders the main headline', () => {
    render(
      <Router>
        <HeroSection />
      </Router>
    );
    expect(screen.getByText('Manage Your Investments with Precision')).toBeInTheDocument();
  });

  it('renders the value proposition', () => {
    render(
      <Router>
        <HeroSection />
      </Router>
    );
    expect(screen.getByText(
      /InvestSmart provides comprehensive portfolio optimization tools/
    )).toBeInTheDocument();
  });

  it('renders Get Started and Learn More buttons', () => {
    render(
      <Router>
        <HeroSection />
      </Router>
    );
    expect(screen.getByText('Get Started')).toBeInTheDocument();
    expect(screen.getByText('Learn More')).toBeInTheDocument();
  });

  it('Get Started button has correct link', () => {
    render(
      <Router>
        <HeroSection />
      </Router>
    );
    expect(screen.getByText('Get Started')).toHaveAttribute('href', '/#get-started');
  });

  it('Learn More button has correct link', () => {
    render(
      <Router>
        <HeroSection />
      </Router>
    );
    expect(screen.getByText('Learn More')).toHaveAttribute('href', '/#learn-more');
  });
});
