import React from 'react';
import { render, screen } from '@testing-library/react';
import Logo from '../../../src/components/LandingPage/Logo';

describe('Logo', () => {
  it('renders the InvestSmart text', () => {
    render(<Logo />);
    expect(screen.getByText('InvestSmart')).toBeInTheDocument();
  });

  it('renders a blue geometric icon placeholder', () => {
    render(<Logo />);
    const svgElement = screen.getByRole('img');
    expect(svgElement).toBeInTheDocument();
    // Check the stroke attribute of the path elements inside the SVG
    const pathElements = svgElement.querySelectorAll('path');
    pathElements.forEach(path => {
      expect(path).toHaveAttribute('stroke', '#3B82F6');
    });
  });
});