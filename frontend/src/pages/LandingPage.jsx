import React, { useState, useEffect } from 'react';
import Logo from '../components/LandingPage/Logo';
import NavigationMenu from '../components/LandingPage/NavigationMenu';
import ActionButtons from '../components/LandingPage/ActionButtons';
import HeroSection from '../components/LandingPage/HeroSection';
import KeyFeaturesSection from '../components/LandingPage/KeyFeaturesSection';
import HowItWorksSection from '../components/LandingPage/HowItWorksSection';

const LandingPage = () => {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Force removal of custom scrollbar (fix for cached PWA styles)
  useEffect(() => {
    const style = document.createElement('style');
    style.innerHTML = `
      ::-webkit-scrollbar {
        width: auto !important;
        background: transparent !important;
      }
      ::-webkit-scrollbar-track {
        background: transparent !important;
      }
      ::-webkit-scrollbar-thumb {
        background: rgba(156, 163, 175, 0.5) !important;
        border-radius: 9999px !important;
        border: 3px solid transparent !important;
        background-clip: content-box !important;
      }
      ::-webkit-scrollbar-thumb:hover {
        background: rgba(156, 163, 175, 0.8) !important;
        border: 3px solid transparent !important;
        background-clip: content-box !important;
      }
    `;
    document.head.appendChild(style);
    return () => {
      document.head.removeChild(style);
    };
  }, []);

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#1f2937' }}>
      {/* Sticky Header */}
      <header 
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled 
            ? 'bg-gray-900/95 backdrop-blur-lg shadow-2xl py-3' 
            : 'bg-transparent py-4'
        }`}
        style={{ 
          backgroundColor: scrolled ? 'var(--color-surface)' : 'transparent',
          boxShadow: scrolled ? 'var(--shadow-md)' : 'none'
        }}
      >
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <Logo />
            <div className="flex items-center space-x-8">
              <NavigationMenu />
              <ActionButtons />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="pt-16">
        <HeroSection />
        <KeyFeaturesSection />
        <HowItWorksSection />
      </main>

      {/* Footer */}
      <footer style={{ 
        backgroundColor: 'var(--color-surface)'
      }}>
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="mb-4 md:mb-0">
              <Logo />
              <p className="text-sm mt-2" style={{ color: 'var(--color-text-secondary)' }}>
                Professional portfolio management for modern investors.
              </p>
            </div>
            <div className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              &copy; {new Date().getFullYear()} InvestSmart. All rights reserved.
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
