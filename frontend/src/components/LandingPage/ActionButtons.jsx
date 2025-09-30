import React, { useState } from 'react';
import { Link } from 'react-router-dom';

const ActionButtons = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <>
      {/* Desktop buttons */}
      <div className="hidden md:flex items-center space-x-3">
        <Link 
          to="/login" 
          className="text-gray-300 hover:text-white text-sm font-medium transition-colors duration-200 px-4 py-2 rounded-lg hover:bg-white/5"
        >
          Log In
        </Link>
        <Link 
          to="/register" 
          className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-5 py-2 rounded-lg text-sm font-semibold hover:shadow-lg hover:shadow-blue-500/50 transition-all duration-300 hover:scale-105"
        >
          Sign Up
        </Link>
      </div>

      {/* Mobile menu button */}
      <button
        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        className="md:hidden text-white p-2 hover:bg-white/10 rounded-lg transition-colors duration-200"
        aria-label="Toggle mobile menu"
      >
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          {mobileMenuOpen ? (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          ) : (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          )}
        </svg>
      </button>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="md:hidden absolute top-full left-0 right-0 bg-gray-900/98 backdrop-blur-lg border-t border-gray-800 shadow-2xl">
          <div className="container mx-auto px-4 py-6 space-y-4">
            <Link 
              to="/login"
              className="block text-center py-3 text-white hover:bg-white/10 rounded-lg transition-colors duration-200"
              onClick={() => setMobileMenuOpen(false)}
            >
              Log In
            </Link>
            <Link 
              to="/register"
              className="block text-center py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-semibold hover:shadow-lg hover:shadow-blue-500/50 transition-all duration-300"
              onClick={() => setMobileMenuOpen(false)}
            >
              Sign Up
            </Link>
          </div>
        </div>
      )}
    </>
  );
};

export default ActionButtons;
