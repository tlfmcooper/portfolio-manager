import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Home, PieChart, BarChart3, RefreshCw, LogOut, User, Sun, Moon, X } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const Sidebar = ({ sidebarOpen, setSidebarOpen, darkMode, toggleDarkMode }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const navigation = [
    { name: 'Overview', href: '/dashboard/overview', icon: Home },
    { name: 'Portfolio', href: '/dashboard/portfolio', icon: PieChart },
    { name: 'Analytics', href: '/dashboard/analytics', icon: BarChart3 },
    { name: 'Update Portfolio', href: '/dashboard/update-portfolio', icon: RefreshCw },
  ];

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <>
      {/* Mobile sidebar */}
      <div className={`fixed inset-0 flex z-40 md:hidden ${sidebarOpen ? 'block' : 'hidden'}`}>
        <div className="fixed inset-0">
          <div className="absolute inset-0 bg-black opacity-50" onClick={() => setSidebarOpen(false)}></div>
        </div>
        <div className="relative flex-1 flex flex-col max-w-xs w-full" style={{ backgroundColor: 'var(--color-surface)' }}>
          <div className="absolute top-0 right-0 -mr-14 p-1">
            <button
              onClick={() => setSidebarOpen(false)}
              className="flex items-center justify-center h-12 w-12 rounded-full focus:outline-none"
              style={{ backgroundColor: 'rgba(0, 0, 0, 0.1)' }}
            >
              <X className="h-6 w-6" style={{ color: 'var(--color-white)' }} />
            </button>
          </div>
          <div className="flex-1 h-0 pt-5 pb-4 overflow-y-auto">
            <div className="flex-shrink-0 flex items-center px-4">
              <h1 className="text-xl font-bold" style={{ color: 'var(--color-text)' }}>Portfolio Dashboard</h1>
            </div>
            <nav className="mt-5 px-2 space-y-1">
              {navigation.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.name}
                    to={item.href}
                    className={({ isActive }) =>
                      `group flex items-center px-2 py-2 text-base font-medium rounded-md transition-all ${
                        isActive
                          ? 'text-white'
                          : 'hover:transform hover:translateX-1'
                      }`
                    }
                    style={({ isActive }) => ({
                      backgroundColor: isActive ? 'var(--color-primary)' : 'transparent',
                      color: isActive ? 'var(--color-btn-primary-text)' : 'var(--color-text-secondary)'
                    })}
                    onClick={() => setSidebarOpen(false)}
                  >
                    <Icon
                      className="mr-4 h-6 w-6"
                      style={{ color: 'inherit' }}
                      aria-hidden="true"
                    />
                    {item.name}
                  </NavLink>
                );
              })}
            </nav>
          </div>
          <div className="flex-shrink-0 flex border-t p-4" style={{ borderColor: 'var(--color-border)' }}>
            <div className="flex items-center">
              <div className="h-9 w-9 rounded-full flex items-center justify-center" style={{ backgroundColor: 'var(--color-primary)' }}>
                <User className="h-5 w-5" style={{ color: 'var(--color-btn-primary-text)' }} />
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>{user?.username || 'User'}</p>
                <p className="text-xs font-medium" style={{ color: 'var(--color-text-secondary)' }}>{user?.email || ''}</p>
              </div>
            </div>
            <div className="ml-auto flex items-center">
              <button
                onClick={toggleDarkMode}
                className="p-1 rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 mr-2 transition-all duration-200"
                style={{ 
                  color: 'var(--color-text-secondary)',
                  focusRingColor: 'var(--color-primary)'
                }}
                title="Toggle Dark Mode"
              >
                {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
              </button>
              <button
                onClick={handleLogout}
                className="p-1 rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 transition-all duration-200"
                style={{ 
                  color: 'var(--color-text-secondary)',
                  focusRingColor: 'var(--color-primary)'
                }}
                title="Sign out"
              >
                <LogOut className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
        <div className="flex-shrink-0 w-14"></div>
      </div>

      {/* Static sidebar for desktop */}
      <div className="hidden md:flex md:flex-shrink-0">
        <div className="flex flex-col w-64 border-r" style={{ 
          borderColor: 'var(--color-border)', 
          backgroundColor: 'var(--color-surface)' 
        }}>
          <div className="flex-1 flex flex-col pt-5 pb-4 overflow-y-auto">
            <div className="flex items-center flex-shrink-0 px-4">
              <h1 className="text-xl font-bold" style={{ color: 'var(--color-text)' }}>Portfolio Dashboard</h1>
            </div>
            <nav className="mt-5 flex-1 px-2 space-y-1" style={{ backgroundColor: 'var(--color-surface)' }}>
              {navigation.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.name}
                    to={item.href}
                    className={({ isActive }) =>
                      `group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-all duration-200 ${
                        isActive
                          ? ''
                          : 'hover:transform hover:translateX-1'
                      }`
                    }
                    style={({ isActive }) => ({
                      backgroundColor: isActive ? 'var(--color-primary)' : 'transparent',
                      color: isActive ? 'var(--color-btn-primary-text)' : 'var(--color-text-secondary)'
                    })}
                  >
                    <Icon
                      className="mr-3 h-6 w-6"
                      style={{ color: 'inherit' }}
                      aria-hidden="true"
                    />
                    {item.name}
                  </NavLink>
                );
              })}
            </nav>
          </div>
          <div className="flex-shrink-0 flex border-t p-4" style={{ borderColor: 'var(--color-border)' }}>
            <div className="flex items-center">
              <div className="h-9 w-9 rounded-full flex items-center justify-center" style={{ backgroundColor: 'var(--color-primary)' }}>
                <User className="h-5 w-5" style={{ color: 'var(--color-btn-primary-text)' }} />
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>{user?.username || 'User'}</p>
                <p className="text-xs font-medium" style={{ color: 'var(--color-text-secondary)' }}>{user?.email || ''}</p>
              </div>
            </div>
            <div className="ml-auto flex items-center">
              <button
                onClick={toggleDarkMode}
                className="p-1 rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 mr-2 transition-all duration-200"
                style={{ 
                  color: 'var(--color-text-secondary)',
                  focusRingColor: 'var(--color-primary)'
                }}
                title="Toggle Dark Mode"
              >
                {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
              </button>
              <button
                onClick={handleLogout}
                className="p-1 rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 transition-all duration-200"
                style={{ 
                  color: 'var(--color-text-secondary)',
                  focusRingColor: 'var(--color-primary)'
                }}
                title="Sign out"
              >
                <LogOut className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default Sidebar;
