import { useState, useRef, useEffect } from 'react';
import { Sun, Moon, Monitor } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

/**
 * ThemeToggle Component
 * Provides a dropdown menu to switch between light, dark, and system themes
 * with visual indicators of the current theme
 */
export function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const themes = [
    {
      id: 'light',
      label: 'Light',
      icon: Sun,
      description: 'Light theme',
    },
    {
      id: 'dark',
      label: 'Dark',
      icon: Moon,
      description: 'Dark theme',
    },
    {
      id: 'system',
      label: 'System',
      icon: Monitor,
      description: 'Follow system preference',
    },
  ];

  const getCurrentIcon = () => {
    if (theme === 'system') {
      return resolvedTheme === 'dark' ? Moon : Sun;
    }
    return theme === 'dark' ? Moon : Sun;
  };

  const getCurrentLabel = () => {
    if (theme === 'system') {
      return `System (${resolvedTheme === 'dark' ? 'Dark' : 'Light'})`;
    }
    return theme.charAt(0).toUpperCase() + theme.slice(1);
  };

  const CurrentIcon = getCurrentIcon();

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2"
        style={{
          backgroundColor: 'var(--color-secondary)',
          color: 'var(--color-text)',
          borderRadius: 'var(--radius-base)',
          border: '1px solid var(--color-border)',
          fontSize: 'var(--font-size-sm)',
          fontWeight: 'var(--font-weight-medium)',
        }}
        title={`Theme: ${getCurrentLabel()}`}
        aria-label="Toggle theme"
        aria-expanded={isOpen}
      >
        <CurrentIcon className="h-4 w-4" />
        <span className="hidden sm:inline">{getCurrentLabel()}</span>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          className="absolute right-0 mt-2 w-48 rounded-lg shadow-lg z-50 animate-fade-in"
          style={{
            backgroundColor: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            boxShadow: 'var(--shadow-lg)',
          }}
        >
          <div className="py-1">
            {themes.map((themeOption) => {
              const ThemeIcon = themeOption.icon;
              const isActive = theme === themeOption.id;

              return (
                <button
                  key={themeOption.id}
                  onClick={() => {
                    setTheme(themeOption.id);
                    setIsOpen(false);
                  }}
                  className="w-full flex items-center gap-3 px-4 py-2 text-left transition-colors duration-150 focus:outline-none"
                  style={{
                    backgroundColor: isActive
                      ? 'var(--color-primary-light)'
                      : 'transparent',
                    color: isActive ? 'var(--color-primary)' : 'var(--color-text)',
                    fontSize: 'var(--font-size-sm)',
                  }}
                  aria-current={isActive ? 'true' : 'false'}
                >
                  <ThemeIcon className="h-5 w-5 flex-shrink-0" />
                  <div className="flex-1">
                    <div className="font-medium">{themeOption.label}</div>
                    <div
                      className="text-xs"
                      style={{
                        color: isActive
                          ? 'var(--color-primary-hover)'
                          : 'var(--color-text-secondary)',
                      }}
                    >
                      {themeOption.description}
                    </div>
                  </div>
                  {isActive && (
                    <div
                      className="h-2 w-2 rounded-full flex-shrink-0"
                      style={{ backgroundColor: 'var(--color-primary)' }}
                      aria-hidden="true"
                    />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default ThemeToggle;
