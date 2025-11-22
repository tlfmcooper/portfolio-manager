import { createContext, useContext, useEffect, useState } from 'react';

// Create the theme context
const ThemeContext = createContext(null);

/**
 * ThemeProvider Component
 * Manages theme state (light, dark, system) with local storage persistence
 * and system preference detection
 */
export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    // Try to get stored theme preference
    const storedTheme = localStorage.getItem('theme');
    if (storedTheme) {
      return storedTheme;
    }
    // Default to light mode instead of system preference
    return 'light';
  });

  const [resolvedTheme, setResolvedTheme] = useState(() => {
    const storedTheme = localStorage.getItem('theme');
    if (storedTheme === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return storedTheme || 'light';
  });

  // Effect to apply theme to DOM and persist to localStorage
  useEffect(() => {
    const root = document.documentElement;

    // Determine the actual theme to apply
    let actualTheme = theme;
    if (theme === 'system') {
      const isSystemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      actualTheme = isSystemDark ? 'dark' : 'light';
    }

    // Apply theme to DOM
    root.classList.remove('light', 'dark');
    root.classList.add(actualTheme);
    root.setAttribute('data-theme', actualTheme);

    // Also set the data-color-scheme for backward compatibility
    root.setAttribute('data-color-scheme', actualTheme);

    // Update resolved theme state
    setResolvedTheme(actualTheme);

    // Persist preference to localStorage
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Listen for system theme changes when theme is set to 'system'
  useEffect(() => {
    if (theme !== 'system') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (e) => {
      const root = document.documentElement;
      const newTheme = e.matches ? 'dark' : 'light';
      root.classList.remove('light', 'dark');
      root.classList.add(newTheme);
      root.setAttribute('data-theme', newTheme);
      root.setAttribute('data-color-scheme', newTheme);
      setResolvedTheme(newTheme);
    };

    // Use addEventListener for better browser compatibility
    mediaQuery.addEventListener('change', handleChange);

    return () => {
      mediaQuery.removeEventListener('change', handleChange);
    };
  }, [theme]);

  const value = {
    theme,
    setTheme,
    resolvedTheme,
    toggleTheme: () => {
      setTheme((prev) => {
        if (prev === 'light') return 'dark';
        if (prev === 'dark') return 'system';
        return 'light';
      });
    },
    isDark: resolvedTheme === 'dark',
    isLight: resolvedTheme === 'light',
  };

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

/**
 * useTheme Hook
 * Use this hook to access theme context in any component
 * @returns {Object} Theme context object with theme state and setters
 * @throws {Error} If used outside of ThemeProvider
 */
export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};

export default ThemeContext;
