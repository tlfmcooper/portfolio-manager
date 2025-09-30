import React from 'react';

const Logo = () => {
  return (
    <div className="flex items-center space-x-2 group cursor-pointer">
      {/* Modern gradient logo */}
      <div className="relative">
        <svg 
          width="32" 
          height="32" 
          viewBox="0 0 40 40" 
          fill="none" 
          xmlns="http://www.w3.org/2000/svg" 
          className="transform group-hover:scale-110 transition-transform duration-300"
          role="img" 
          aria-label="InvestSmart logo"
        >
          <defs>
            <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#3B82F6" />
              <stop offset="100%" stopColor="#8B5CF6" />
            </linearGradient>
          </defs>
          <circle cx="20" cy="20" r="18" fill="url(#logoGradient)" opacity="0.2"/>
          <path d="M20 8L10 14V26L20 32L30 26V14L20 8Z" stroke="url(#logoGradient)" strokeWidth="2.5" strokeLinejoin="round"/>
          <path d="M20 14L25 17L20 20L15 17L20 14Z" stroke="url(#logoGradient)" strokeWidth="2.5" strokeLinejoin="round"/>
          <circle cx="20" cy="20" r="3" fill="url(#logoGradient)"/>
        </svg>
      </div>
      <span className="text-white text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
        InvestSmart
      </span>
    </div>
  );
};

export default Logo;
