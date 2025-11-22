import { useEffect, useState } from 'react';
import { WifiOff, Wifi } from 'lucide-react';

/**
 * OfflineIndicator Component
 *
 * Displays a banner at the top when the user is offline.
 * Uses navigator.onLine and listens to online/offline events.
 *
 * Features:
 * - Fixed positioning at top with z-index 50
 * - Orange/yellow background when offline
 * - Lucide icons (WifiOff for offline, Wifi for online)
 * - Hides automatically when online
 * - Tailwind CSS styling
 *
 * Usage: <OfflineIndicator /> - Place at top level of App
 */
export function OfflineIndicator() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  if (isOnline) return null;

  return (
    <div className="fixed top-0 left-0 right-0 bg-amber-500 text-white py-2 px-4 text-center z-50 flex items-center justify-center gap-2 shadow-md">
      <WifiOff className="h-4 w-4" />
      <span className="text-sm font-medium">
        You're offline. Viewing cached data.
      </span>
    </div>
  );
}

export default OfflineIndicator;
