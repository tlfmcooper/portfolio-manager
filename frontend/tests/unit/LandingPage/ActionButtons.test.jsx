import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter as Router } from 'react-router-dom';
import ActionButtons from '../../../src/components/LandingPage/ActionButtons';

describe('ActionButtons', () => {
  it('renders Log In and Sign Up buttons', () => {
    render(
      <Router>
        <ActionButtons />
      </Router>
    );
    expect(screen.getByText('Log In')).toBeInTheDocument();
    expect(screen.getByText('Sign Up')).toBeInTheDocument();
  });

  it('Log In button has correct link', () => {
    render(
      <Router>
        <ActionButtons />
      </Router>
    );
    expect(screen.getByText('Log In')).toHaveAttribute('href', '/login');
  });

  it('Sign Up button has correct link', () => {
    render(
      <Router>
        <ActionButtons />
      </Router>
    );
    expect(screen.getByText('Sign Up')).toHaveAttribute('href', '/register');
  });
});
