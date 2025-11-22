/**
 * Offline Storage Service
 *
 * Provides persistent offline storage using localforage (IndexedDB/localStorage)
 * for the Portfolio Dashboard. Handles caching of portfolio data, holdings,
 * analytics, and user preferences with automatic expiry management.
 *
 * Phase 2: Offline Data Persistence (Section 2.2, 2.3)
 */

import localforage from 'localforage';

// Storage keys
const STORAGE_KEYS = {
  PORTFOLIO: 'portfolio_data',
  HOLDINGS: 'holdings_data',
  ANALYTICS: 'analytics_data',
  ANALYTICS_TIMESTAMP: 'analytics_timestamp',
  USER_PREFERENCES: 'user_preferences',
  STORAGE_METADATA: 'storage_metadata',
};

// Cache expiry times (in milliseconds)
const CACHE_EXPIRY = {
  ANALYTICS: 1 * 60 * 60 * 1000, // 1 hour
  DEFAULT: 24 * 60 * 60 * 1000,   // 24 hours
};

/**
 * OfflineStorageService
 *
 * Handles all offline storage operations for the portfolio dashboard.
 * Provides methods to save/retrieve data with timestamp-based cache expiry.
 */
class OfflineStorageService {
  constructor() {
    this.initialized = false;
    this.dbName = 'portfolio-dashboard-offline';
    this.dbVersion = 1;
    this.ready = this.init();
  }

  /**
   * Initialize localforage with custom configuration
   */
  async init() {
    try {
      await localforage.config({
        name: this.dbName,
        version: this.dbVersion,
        storeName: 'offline_cache',
        description: 'Portfolio Dashboard offline storage',
      });
      this.initialized = true;
      console.log('[OfflineStorage] Initialized successfully');
      return true;
    } catch (error) {
      console.error('[OfflineStorage] Initialization failed:', error);
      this.initialized = false;
      return false;
    }
  }

  /**
   * Ensure storage is ready before operations
   */
  async ensureReady() {
    if (!this.initialized) {
      await this.ready;
    }
  }

  /**
   * Save portfolio data to offline storage
   * @param {Object} portfolioData - Portfolio data to save
   * @returns {Promise<boolean>} - Success status
   */
  async savePortfolio(portfolioData) {
    try {
      await this.ensureReady();
      const timestamp = Date.now();
      await localforage.setItem(STORAGE_KEYS.PORTFOLIO, {
        data: portfolioData,
        timestamp,
      });
      console.log('[OfflineStorage] Portfolio saved at', new Date(timestamp).toISOString());
      return true;
    } catch (error) {
      console.error('[OfflineStorage] Failed to save portfolio:', error);
      return false;
    }
  }

  /**
   * Get portfolio data from offline storage
   * @returns {Promise<Object|null>} - Portfolio data or null if not found
   */
  async getPortfolio() {
    try {
      await this.ensureReady();
      const stored = await localforage.getItem(STORAGE_KEYS.PORTFOLIO);
      if (!stored) {
        console.log('[OfflineStorage] No cached portfolio data found');
        return null;
      }
      console.log('[OfflineStorage] Retrieved portfolio data from cache');
      return stored.data;
    } catch (error) {
      console.error('[OfflineStorage] Failed to retrieve portfolio:', error);
      return null;
    }
  }

  /**
   * Save holdings data to offline storage
   * @param {Array} holdingsData - Holdings array to save
   * @returns {Promise<boolean>} - Success status
   */
  async saveHoldings(holdingsData) {
    try {
      await this.ensureReady();
      const timestamp = Date.now();
      await localforage.setItem(STORAGE_KEYS.HOLDINGS, {
        data: holdingsData,
        timestamp,
      });
      console.log('[OfflineStorage] Holdings saved at', new Date(timestamp).toISOString());
      return true;
    } catch (error) {
      console.error('[OfflineStorage] Failed to save holdings:', error);
      return false;
    }
  }

  /**
   * Get holdings data from offline storage
   * @returns {Promise<Array|null>} - Holdings array or null if not found
   */
  async getHoldings() {
    try {
      await this.ensureReady();
      const stored = await localforage.getItem(STORAGE_KEYS.HOLDINGS);
      if (!stored) {
        console.log('[OfflineStorage] No cached holdings data found');
        return null;
      }
      console.log('[OfflineStorage] Retrieved holdings data from cache');
      return stored.data;
    } catch (error) {
      console.error('[OfflineStorage] Failed to retrieve holdings:', error);
      return null;
    }
  }

  /**
   * Save analytics data with timestamp for cache expiry checking
   * @param {Object} analyticsData - Analytics data to save
   * @returns {Promise<boolean>} - Success status
   */
  async saveAnalytics(analyticsData) {
    try {
      await this.ensureReady();
      const timestamp = Date.now();
      await localforage.setItem(STORAGE_KEYS.ANALYTICS, {
        data: analyticsData,
        timestamp,
      });
      // Also save timestamp separately for quick expiry checks
      await localforage.setItem(STORAGE_KEYS.ANALYTICS_TIMESTAMP, timestamp);
      console.log('[OfflineStorage] Analytics saved at', new Date(timestamp).toISOString());
      return true;
    } catch (error) {
      console.error('[OfflineStorage] Failed to save analytics:', error);
      return false;
    }
  }

  /**
   * Get analytics data if not expired (1 hour cache)
   * @returns {Promise<Object|null>} - Analytics data or null if expired/not found
   */
  async getAnalytics() {
    try {
      await this.ensureReady();
      const stored = await localforage.getItem(STORAGE_KEYS.ANALYTICS);
      if (!stored) {
        console.log('[OfflineStorage] No cached analytics data found');
        return null;
      }

      const age = Date.now() - stored.timestamp;
      const isExpired = age > CACHE_EXPIRY.ANALYTICS;

      if (isExpired) {
        console.log('[OfflineStorage] Analytics data expired (age:', Math.round(age / 1000), 'seconds)');
        // Don't remove it yet - it might still be useful, just expired
        return null;
      }

      const remainingTime = Math.round((CACHE_EXPIRY.ANALYTICS - age) / 1000);
      console.log('[OfflineStorage] Retrieved analytics from cache (expires in', remainingTime, 'seconds)');
      return stored.data;
    } catch (error) {
      console.error('[OfflineStorage] Failed to retrieve analytics:', error);
      return null;
    }
  }

  /**
   * Get analytics cache age in seconds
   * @returns {Promise<number|null>} - Age in seconds or null if not found
   */
  async getAnalyticsCacheAge() {
    try {
      await this.ensureReady();
      const timestamp = await localforage.getItem(STORAGE_KEYS.ANALYTICS_TIMESTAMP);
      if (!timestamp) {
        return null;
      }
      return Math.round((Date.now() - timestamp) / 1000);
    } catch (error) {
      console.error('[OfflineStorage] Failed to get analytics cache age:', error);
      return null;
    }
  }

  /**
   * Save user preferences
   * @param {Object} preferences - User preferences object
   * @returns {Promise<boolean>} - Success status
   */
  async saveUserPreferences(preferences) {
    try {
      await this.ensureReady();
      const timestamp = Date.now();
      await localforage.setItem(STORAGE_KEYS.USER_PREFERENCES, {
        data: preferences,
        timestamp,
      });
      console.log('[OfflineStorage] User preferences saved');
      return true;
    } catch (error) {
      console.error('[OfflineStorage] Failed to save user preferences:', error);
      return false;
    }
  }

  /**
   * Get user preferences
   * @returns {Promise<Object|null>} - User preferences or null if not found
   */
  async getUserPreferences() {
    try {
      await this.ensureReady();
      const stored = await localforage.getItem(STORAGE_KEYS.USER_PREFERENCES);
      if (!stored) {
        console.log('[OfflineStorage] No cached user preferences found');
        return null;
      }
      console.log('[OfflineStorage] Retrieved user preferences from cache');
      return stored.data;
    } catch (error) {
      console.error('[OfflineStorage] Failed to retrieve user preferences:', error);
      return null;
    }
  }

  /**
   * Get storage statistics and information
   * @returns {Promise<Object>} - Storage info including sizes and cache ages
   */
  async getStorageInfo() {
    try {
      await this.ensureReady();

      const info = {
        initialized: this.initialized,
        dbName: this.dbName,
        timestamp: new Date().toISOString(),
        data: {},
      };

      // Get all stored items with their metadata
      const items = [
        { key: STORAGE_KEYS.PORTFOLIO, label: 'Portfolio' },
        { key: STORAGE_KEYS.HOLDINGS, label: 'Holdings' },
        { key: STORAGE_KEYS.ANALYTICS, label: 'Analytics' },
        { key: STORAGE_KEYS.USER_PREFERENCES, label: 'User Preferences' },
      ];

      for (const item of items) {
        const stored = await localforage.getItem(item.key);
        if (stored) {
          const size = new Blob([JSON.stringify(stored)]).size;
          const age = Math.round((Date.now() - stored.timestamp) / 1000);
          info.data[item.label] = {
            exists: true,
            sizeKB: (size / 1024).toFixed(2),
            ageSeconds: age,
            timestamp: new Date(stored.timestamp).toISOString(),
            expiresInSeconds: item.key === STORAGE_KEYS.ANALYTICS
              ? Math.round((CACHE_EXPIRY.ANALYTICS - age) / 1000)
              : null,
          };
        } else {
          info.data[item.label] = {
            exists: false,
          };
        }
      }

      // Calculate total size
      let totalSize = 0;
      for (const itemInfo of Object.values(info.data)) {
        if (itemInfo.exists) {
          totalSize += parseFloat(itemInfo.sizeKB);
        }
      }
      info.totalSizeKB = totalSize.toFixed(2);

      console.log('[OfflineStorage] Storage info retrieved:', info);
      return info;
    } catch (error) {
      console.error('[OfflineStorage] Failed to get storage info:', error);
      return {
        initialized: this.initialized,
        error: error.message,
      };
    }
  }

  /**
   * Clear all offline storage data
   * @returns {Promise<boolean>} - Success status
   */
  async clearAll() {
    try {
      await this.ensureReady();
      await localforage.clear();
      console.log('[OfflineStorage] All data cleared');
      return true;
    } catch (error) {
      console.error('[OfflineStorage] Failed to clear storage:', error);
      return false;
    }
  }

  /**
   * Clear specific data types
   * @param {Array<string>} keys - Storage keys to clear
   * @returns {Promise<boolean>} - Success status
   */
  async clearSpecific(keys) {
    try {
      await this.ensureReady();
      for (const key of keys) {
        await localforage.removeItem(key);
      }
      console.log('[OfflineStorage] Cleared keys:', keys);
      return true;
    } catch (error) {
      console.error('[OfflineStorage] Failed to clear specific data:', error);
      return false;
    }
  }

  /**
   * Clear expired analytics data
   * @returns {Promise<boolean>} - Success status
   */
  async clearExpiredAnalytics() {
    try {
      await this.ensureReady();
      const stored = await localforage.getItem(STORAGE_KEYS.ANALYTICS);
      if (!stored) {
        return true;
      }

      const age = Date.now() - stored.timestamp;
      const isExpired = age > CACHE_EXPIRY.ANALYTICS;

      if (isExpired) {
        await localforage.removeItem(STORAGE_KEYS.ANALYTICS);
        await localforage.removeItem(STORAGE_KEYS.ANALYTICS_TIMESTAMP);
        console.log('[OfflineStorage] Expired analytics cleared');
      }
      return true;
    } catch (error) {
      console.error('[OfflineStorage] Failed to clear expired analytics:', error);
      return false;
    }
  }

  /**
   * Export all storage data for backup
   * @returns {Promise<Object>} - All storage data
   */
  async exportAll() {
    try {
      await this.ensureReady();
      const exported = {};
      const keys = await localforage.keys();

      for (const key of keys) {
        exported[key] = await localforage.getItem(key);
      }

      console.log('[OfflineStorage] Exported', Object.keys(exported).length, 'items');
      return exported;
    } catch (error) {
      console.error('[OfflineStorage] Failed to export storage:', error);
      return null;
    }
  }

  /**
   * Import storage data from backup
   * @param {Object} data - Data to import
   * @returns {Promise<boolean>} - Success status
   */
  async importAll(data) {
    try {
      await this.ensureReady();
      for (const [key, value] of Object.entries(data)) {
        await localforage.setItem(key, value);
      }
      console.log('[OfflineStorage] Imported', Object.keys(data).length, 'items');
      return true;
    } catch (error) {
      console.error('[OfflineStorage] Failed to import storage:', error);
      return false;
    }
  }
}

// Create singleton instance
const offlineStorage = new OfflineStorageService();

export default offlineStorage;
export { OfflineStorageService, STORAGE_KEYS, CACHE_EXPIRY };
