/**
 * Portfolio API service for frontend
 */

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

export class PortfolioService {
  constructor(api) {
    this.api = api;
  }

  // Portfolio endpoints
  async getPortfolio() {
    const response = await this.api.get('/portfolios/');
    return response.data;
  }

  async updatePortfolio(portfolioData) {
    const response = await this.api.put('/portfolios/', portfolioData);
    return response.data;
  }

  async getPortfolioSummary(currency = null) {
    const params = currency ? { currency } : {};
    const response = await this.api.get('/portfolios/summary', { params });
    return response.data;
  }

  async getPortfolioMetrics(currency = null) {
    const params = currency ? { currency } : {};
    const response = await this.api.get('/portfolios/metrics', { params });
    return response.data;
  }

  async getPortfolioAnalysis(currency = null) {
    const params = currency ? { currency } : {};
    const response = await this.api.get('/portfolios/analysis', { params });
    return response.data;
  }

  async refreshPortfolioMetrics() {
    const response = await this.api.post('/portfolios/refresh-metrics');
    return response.data;
  }

  // Holdings endpoints
  async getHoldings() {
    const response = await this.api.get('/holdings/');
    return response.data;
  }

  async createHolding(holdingData) {
    const response = await this.api.post('/holdings/', holdingData);
    return response.data;
  }

  async updateHolding(holdingId, holdingData) {
    const response = await this.api.put(`/holdings/${holdingId}`, holdingData);
    return response.data;
  }

  async deleteHolding(holdingId) {
    const response = await this.api.delete(`/holdings/${holdingId}`);
    return response.data;
  }

  async getHolding(holdingId) {
    const response = await this.api.get(`/holdings/${holdingId}`);
    return response.data;
  }

  // User endpoints
  async getUserProfile() {
    const response = await this.api.get('/users/me');
    return response.data;
  }

  async updateUserProfile(userData) {
    const response = await this.api.put('/users/me', userData);
    return response.data;
  }

  // Health check
  async healthCheck() {
    const response = await this.api.get('/health');
    return response.data;
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
