import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter as Router } from 'react-router-dom';
import NavigationMenu from '../../../src/components/LandingPage/NavigationMenu';

describe('NavigationMenu', () => {
  it('renders all navigation items', () => {
    render(
      <Router>
        <NavigationMenu />
      </Router>
    );
    const navItems = [
      'Overview',
      'Risk Analytics',
      'Asset Allocation',
      'Simulations',
      'Realtime Data',
    ];
    navItems.forEach((item) => {
      expect(screen.getByText(item)).toBeInTheDocument();
    });
  });

  it('renders correct links for navigation items', () => {
    render(
      <Router>
        <NavigationMenu />
      </Router>
    );
    expect(screen.getByText('Overview')).toHaveAttribute('href', '/dashboard/Overview');
    expect(screen.getByText('Risk Analytics')).toHaveAttribute('href', '/dashboard/analytics');
    expect(screen.getByText('Asset Allocation')).toHaveAttribute('href', '/dashboard/portfolio');
    expect(screen.getByText('Simulations')).toHaveAttribute('href', '/#simulations');
    expect(screen.getByText('Realtime Data')).toHaveAttribute('href', '/#realtime-data');
  });
});
