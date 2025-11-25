/**
 * Portfolio API service for frontend
 *
 * Provides offline fallback capabilities using IndexedDB caching.
 * When offline, cached data is returned. When online, requests are made
 * and responses are cached for offline use.
 *
 * Phase 2: Offline Data Persistence with Cache Fallback (Section 2.2, 2.3)
 */

import offlineStorage from './offlineStorage.js';

export class PortfolioService {
  constructor(api) {
    this.api = api;
    this.isOnline = navigator.onLine;

    // Listen for online/offline events
    window.addEventListener('online', () => {
      this.isOnline = true;
      console.log('[PortfolioService] Back online');
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
      console.log('[PortfolioService] Gone offline');
    });
  }

  /**
   * Check if we're currently online
   */
  checkOnlineStatus() {
    this.isOnline = navigator.onLine;
    return this.isOnline;
  }

  // Portfolio endpoints

  /**
   * Get portfolio data with offline fallback
   */
  async getPortfolio() {
    if (this.checkOnlineStatus()) {
      try {
        const response = await this.api.get('/portfolios/');
        // Cache successful response
        await offlineStorage.savePortfolio(response.data);
        console.log('[PortfolioService] Portfolio cached from API response');
        return response.data;
      } catch (error) {
        console.error('[PortfolioService] API error, attempting offline fallback:', error.message);
        return await this.getPortfolioOffline();
      }
    } else {
      console.log('[PortfolioService] Offline - using cached portfolio');
      return await this.getPortfolioOffline();
    }
  }

  /**
   * Get portfolio from offline cache
   */
  async getPortfolioOffline() {
    const cached = await offlineStorage.getPortfolio();
    if (cached) {
      console.log('[PortfolioService] Using cached portfolio data');
      return cached;
    }
    // Return mock data if no cache available
    console.log('[PortfolioService] No cache available, returning mock data');
    return this.getMockPortfolioData().portfolio;
  }

  async updatePortfolio(portfolioData) {
    if (this.checkOnlineStatus()) {
      try {
        const response = await this.api.put('/portfolios/', portfolioData);
        // Cache successful response
        await offlineStorage.savePortfolio(response.data);
        console.log('[PortfolioService] Portfolio updated and cached');
        return response.data;
      } catch (error) {
        console.error('[PortfolioService] API error updating portfolio:', error.message);
        // Cache the data locally anyway for eventual sync
        await offlineStorage.savePortfolio(portfolioData);
        return portfolioData;
      }
    } else {
      console.log('[PortfolioService] Offline - caching portfolio for later sync');
      await offlineStorage.savePortfolio(portfolioData);
      return portfolioData;
    }
  }

  async getPortfolioSummary(currency = null) {
    const params = currency ? { currency } : {};
    if (this.checkOnlineStatus()) {
      try {
        const response = await this.api.get('/portfolios/summary', { params });
        console.log('[PortfolioService] Portfolio summary retrieved from API');
        return response.data;
      } catch (error) {
        console.error('[PortfolioService] API error getting summary, using cached portfolio:', error.message);
        const cached = await offlineStorage.getPortfolio();
        return cached || this.getMockPortfolioData().portfolio;
      }
    } else {
      console.log('[PortfolioService] Offline - returning cached portfolio as summary');
      const cached = await offlineStorage.getPortfolio();
      return cached || this.getMockPortfolioData().portfolio;
    }
  }

  async getPortfolioMetrics(currency = null) {
    const params = currency ? { currency } : {};
    if (this.checkOnlineStatus()) {
      try {
        const response = await this.api.get('/portfolios/metrics', { params });
        // Cache metrics as part of analytics
        await offlineStorage.saveAnalytics(response.data);
        console.log('[PortfolioService] Portfolio metrics cached from API response');
        return response.data;
      } catch (error) {
        console.error('[PortfolioService] API error, attempting offline fallback:', error.message);
        return await this.getPortfolioMetricsOffline();
      }
    } else {
      console.log('[PortfolioService] Offline - using cached portfolio metrics');
      return await this.getPortfolioMetricsOffline();
    }
  }

  /**
   * Get portfolio metrics from offline cache
   */
  async getPortfolioMetricsOffline() {
    const cached = await offlineStorage.getAnalytics();
    if (cached) {
      console.log('[PortfolioService] Using cached metrics data');
      return cached;
    }
    // Return mock data if no cache available
    console.log('[PortfolioService] No metrics cache available, returning mock data');
    return this.getMockPortfolioData().portfolio_metrics;
  }

  async getPortfolioAnalysis(currency = null) {
    const params = currency ? { currency } : {};
    if (this.checkOnlineStatus()) {
      try {
        const response = await this.api.get('/portfolios/analysis', { params });
        // Cache analysis
        await offlineStorage.saveAnalytics(response.data);
        console.log('[PortfolioService] Portfolio analysis cached from API response');
        return response.data;
      } catch (error) {
        console.error('[PortfolioService] API error, attempting offline fallback:', error.message);
        return await this.getPortfolioAnalysisOffline();
      }
    } else {
      console.log('[PortfolioService] Offline - using cached portfolio analysis');
      return await this.getPortfolioAnalysisOffline();
    }
  }

  /**
   * Get portfolio analysis from offline cache
   */
  async getPortfolioAnalysisOffline() {
    const cached = await offlineStorage.getAnalytics();
    if (cached) {
      console.log('[PortfolioService] Using cached analysis data');
      return cached;
    }
    // Return mock data if no cache available
    console.log('[PortfolioService] No analysis cache available, returning mock data');
    return {
      ...this.getMockPortfolioData().risk_analytics,
      asset_allocation: this.getMockPortfolioData().asset_allocation,
    };
  }

  async refreshPortfolioMetrics() {
    if (this.checkOnlineStatus()) {
      try {
        const response = await this.api.post('/portfolios/refresh-metrics');
        // Cache the refreshed metrics
        await offlineStorage.saveAnalytics(response.data);
        console.log('[PortfolioService] Portfolio metrics refreshed and cached');
        return response.data;
      } catch (error) {
        console.error('[PortfolioService] API error refreshing metrics:', error.message);
        // Return cached metrics
        return await this.getPortfolioMetricsOffline();
      }
    } else {
      console.log('[PortfolioService] Offline - cannot refresh metrics, using cache');
      return await this.getPortfolioMetricsOffline();
    }
  }

  // Holdings endpoints

  /**
   * Get holdings with offline fallback
   */
  async getHoldings() {
    if (this.checkOnlineStatus()) {
      try {
        const response = await this.api.get('/holdings/');
        // Cache successful response
        await offlineStorage.saveHoldings(response.data);
        console.log('[PortfolioService] Holdings cached from API response');
        return response.data;
      } catch (error) {
        console.error('[PortfolioService] API error, attempting offline fallback:', error.message);
        return await this.getHoldingsOffline();
      }
    } else {
      console.log('[PortfolioService] Offline - using cached holdings');
      return await this.getHoldingsOffline();
    }
  }

  /**
   * Get holdings from offline cache
   */
  async getHoldingsOffline() {
    const cached = await offlineStorage.getHoldings();
    if (cached) {
      console.log('[PortfolioService] Using cached holdings data');
      return cached;
    }
    // Return empty array if no cache available
    console.log('[PortfolioService] No holdings cache available, returning empty array');
    return [];
  }

  async createHolding(holdingData) {
    if (this.checkOnlineStatus()) {
      try {
        const response = await this.api.post('/holdings/', holdingData);
        // Update holdings cache
        const cached = await offlineStorage.getHoldings() || [];
        const updated = Array.isArray(cached) ? [...cached, response.data] : [response.data];
        await offlineStorage.saveHoldings(updated);
        console.log('[PortfolioService] Holding created and cached');
        return response.data;
      } catch (error) {
        console.error('[PortfolioService] API error creating holding:', error.message);
        // Cache the data locally for eventual sync
        const cached = await offlineStorage.getHoldings() || [];
        const updated = Array.isArray(cached) ? [...cached, holdingData] : [holdingData];
        await offlineStorage.saveHoldings(updated);
        return holdingData;
      }
    } else {
      console.log('[PortfolioService] Offline - caching holding for later sync');
      const cached = await offlineStorage.getHoldings() || [];
      const updated = Array.isArray(cached) ? [...cached, holdingData] : [holdingData];
      await offlineStorage.saveHoldings(updated);
      return holdingData;
    }
  }

  async updateHolding(holdingId, holdingData) {
    if (this.checkOnlineStatus()) {
      try {
        const response = await this.api.put(`/holdings/${holdingId}`, holdingData);
        // Update holdings cache
        const cached = await offlineStorage.getHoldings() || [];
        const updated = Array.isArray(cached)
          ? cached.map(h => h.id === holdingId ? response.data : h)
          : [response.data];
        await offlineStorage.saveHoldings(updated);
        console.log('[PortfolioService] Holding updated and cached');
        return response.data;
      } catch (error) {
        console.error('[PortfolioService] API error updating holding:', error.message);
        // Cache the data locally for eventual sync
        const cached = await offlineStorage.getHoldings() || [];
        const updated = Array.isArray(cached)
          ? cached.map(h => h.id === holdingId ? holdingData : h)
          : [holdingData];
        await offlineStorage.saveHoldings(updated);
        return holdingData;
      }
    } else {
      console.log('[PortfolioService] Offline - caching holding update for later sync');
      const cached = await offlineStorage.getHoldings() || [];
      const updated = Array.isArray(cached)
        ? cached.map(h => h.id === holdingId ? holdingData : h)
        : [holdingData];
      await offlineStorage.saveHoldings(updated);
      return holdingData;
    }
  }

  async deleteHolding(holdingId) {
    if (this.checkOnlineStatus()) {
      try {
        const response = await this.api.delete(`/holdings/${holdingId}`);
        // Update holdings cache
        const cached = await offlineStorage.getHoldings() || [];
        const updated = Array.isArray(cached)
          ? cached.filter(h => h.id !== holdingId)
          : [];
        await offlineStorage.saveHoldings(updated);
        console.log('[PortfolioService] Holding deleted and cache updated');
        return response.data;
      } catch (error) {
        console.error('[PortfolioService] API error deleting holding:', error.message);
        // Update cache locally for eventual sync
        const cached = await offlineStorage.getHoldings() || [];
        const updated = Array.isArray(cached)
          ? cached.filter(h => h.id !== holdingId)
          : [];
        await offlineStorage.saveHoldings(updated);
        return { success: true, id: holdingId };
      }
    } else {
      console.log('[PortfolioService] Offline - caching holding deletion for later sync');
      const cached = await offlineStorage.getHoldings() || [];
      const updated = Array.isArray(cached)
        ? cached.filter(h => h.id !== holdingId)
        : [];
      await offlineStorage.saveHoldings(updated);
      return { success: true, id: holdingId };
    }
  }

  async getHolding(holdingId) {
    if (this.checkOnlineStatus()) {
      try {
        const response = await this.api.get(`/holdings/${holdingId}`);
        console.log('[PortfolioService] Holding retrieved from API');
        return response.data;
      } catch (error) {
        console.error('[PortfolioService] API error getting holding, using cache:', error.message);
        const cached = await offlineStorage.getHoldings() || [];
        const holding = Array.isArray(cached) ? cached.find(h => h.id === holdingId) : null;
        return holding || null;
      }
    } else {
      console.log('[PortfolioService] Offline - retrieving holding from cache');
      const cached = await offlineStorage.getHoldings() || [];
      const holding = Array.isArray(cached) ? cached.find(h => h.id === holdingId) : null;
      return holding || null;
    }
  }

  // User endpoints

  /**
   * Get user profile with offline fallback
   */
  async getUserProfile() {
    if (this.checkOnlineStatus()) {
      try {
        const response = await this.api.get('/users/me');
        // Cache successful response
        await offlineStorage.saveUserPreferences(response.data);
        console.log('[PortfolioService] User profile cached from API response');
        return response.data;
      } catch (error) {
        console.error('[PortfolioService] API error, attempting offline fallback:', error.message);
        return await this.getUserProfileOffline();
      }
    } else {
      console.log('[PortfolioService] Offline - using cached user profile');
      return await this.getUserProfileOffline();
    }
  }

  /**
   * Get user profile from offline cache
   */
  async getUserProfileOffline() {
    const cached = await offlineStorage.getUserPreferences();
    if (cached) {
      console.log('[PortfolioService] Using cached user profile');
      return cached;
    }
    // Return empty profile if no cache available
    console.log('[PortfolioService] No user profile cache available');
    return null;
  }

  async updateUserProfile(userData) {
    if (this.checkOnlineStatus()) {
      try {
        const response = await this.api.put('/users/me', userData);
        // Cache successful response
        await offlineStorage.saveUserPreferences(response.data);
        console.log('[PortfolioService] User profile updated and cached');
        return response.data;
      } catch (error) {
        console.error('[PortfolioService] API error updating profile:', error.message);
        // Cache the data locally for eventual sync
        await offlineStorage.saveUserPreferences(userData);
        return userData;
      }
    } else {
      console.log('[PortfolioService] Offline - caching user profile for later sync');
      await offlineStorage.saveUserPreferences(userData);
      return userData;
    }
  }

  // Health check

  /**
   * Check API health with fallback to cached status
   */
  async healthCheck() {
    if (this.checkOnlineStatus()) {
      try {
        const response = await this.api.get('/health');
        console.log('[PortfolioService] API health check passed');
        return response.data;
      } catch (error) {
        console.error('[PortfolioService] API health check failed:', error.message);
        return { status: 'offline', message: 'Backend unreachable' };
      }
    } else {
      console.log('[PortfolioService] Device offline - health check unavailable');
      return { status: 'offline', message: 'Device is offline' };
    }
  }

  // Mock data for development (fallback when backend is not available)
  getMockPortfolioData() {
    return {
      portfolio: {
        name: "Sample Portfolio",
        last_updated: new Date().toISOString().split('T')[0],
        total_assets: 5,
        total_value: "$125,450"
      },
      portfolio_metrics: {
        annual_return: 0.125,
        annual_volatility: 0.152,
        sharpe_ratio: 0.82,
        sortino_ratio: 1.15,
        max_drawdown: -0.083,
        calmar_ratio: 1.51,
        compound_return: 0.118,
        skewness: -0.23,
        kurtosis: 0.45
      },
      risk_analytics: {
        var_95: -0.021,
        var_99: -0.034,
        cvar: -0.042,
        portfolio_volatility: 0.152,
        semideviation: 0.098
      },
      asset_allocation: {
        "AAPL": 15.2,
        "GOOGL": 12.8,
        "MSFT": 13.5,
        "SPY": 20.0,
        "QQQ": 10.0,
        "TLT": 8.5,
        "GLD": 7.0,
        "VNQ": 3.0,
        "Others": 10.0
      }
    };
  }
}

export default PortfolioService;
