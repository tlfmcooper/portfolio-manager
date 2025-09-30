import React from 'react';
import { Link } from 'react-router-dom';

const NavigationMenu = () => {
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
            <Link 
              to={item.href} 
              className="relative px-4 py-2 text-gray-300 hover:text-white text-sm font-medium transition-colors duration-200 rounded-lg hover:bg-white/5 group"
            >
              {item.name}
              <span className="absolute bottom-0 left-1/2 transform -translate-x-1/2 w-0 h-0.5 bg-gradient-to-r from-blue-400 to-purple-400 group-hover:w-3/4 transition-all duration-300"></span>
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
};

export default NavigationMenu;
