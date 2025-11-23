import React from 'react';
import { Link } from 'react-router-dom';

const NavigationMenu = () => {
  const scrollToSection = (e, href) => {
    e.preventDefault();
    if (href.startsWith('#')) {
      const element = document.querySelector(href);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
      }
    } else {
      window.location.href = href;
    }
  };

  const navItems = [
    { name: 'Features', href: '#features' },
    { name: 'How It Works', href: '#how-it-works' },
    { name: 'Dashboard', href: '/dashboard/overview' },
  ];

  return (
    <nav className="hidden lg:block">
      <ul className="flex items-center space-x-1">
        {navItems.map((item) => (
          <li key={item.name}>
            <a 
              href={item.href}
              onClick={(e) => scrollToSection(e, item.href)}
              className="relative px-4 py-2 text-gray-300 hover:text-white text-sm font-medium transition-colors duration-200 rounded-lg hover:bg-white/5 group cursor-pointer"
            >
              {item.name}
              <span className="absolute bottom-0 left-1/2 transform -translate-x-1/2 w-0 h-0.5 bg-gradient-to-r from-blue-400 to-purple-400 group-hover:w-3/4 transition-all duration-300"></span>
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
};

export default NavigationMenu;
