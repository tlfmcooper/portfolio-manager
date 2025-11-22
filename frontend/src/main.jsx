import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { registerSW } from 'virtual:pwa-register'

// Register service worker for PWA functionality
const updateSW = registerSW({
  onNeedRefresh() {
    // Show update notification
    const shouldUpdate = confirm(
      'New content available! Click OK to update and refresh the app.'
    );
    if (shouldUpdate) {
      updateSW(true);
    }
  },
  onOfflineReady() {
    console.log('✅ App ready to work offline');
    // You could show a toast notification here
    // For now, we'll just log it
  },
  onRegisterError(error) {
    console.error('❌ Service worker registration error:', error);
  },
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
