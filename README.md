# Advanced Portfolio Dashboard

A comprehensive, professional-grade portfolio management dashboard built with React and FastAPI, featuring real-time market data integration, advanced analytics, risk management tools, and interactive visualizations.

## 🚀 Features

### **Real-Time Data Integration**
- **Live Market Data**: Fetches real-time data from Yahoo Finance for all major assets
- **Automatic Updates**: Portfolio metrics refresh with current market conditions
- **Fallback Support**: Graceful degradation to mock data when market APIs are unavailable
- **Multi-Asset Support**: Stocks, ETFs, bonds, commodities, and international assets

### **Advanced Analytics Engine**
- **Performance Metrics**: Sharpe ratio, Sortino ratio, Calmar ratio, maximum drawdown
- **Risk Analytics**: VaR (95%, 99%), CVaR, semideviation, portfolio volatility
- **Higher Moments**: Skewness, kurtosis, compound returns analysis
- **Attribution Analysis**: Individual asset performance and contribution tracking

### **Professional Visualizations**

#### **1. Overview Section**
- **Performance Overview**: Interactive bar charts showing returns vs volatility
- **Key Metrics Grid**: Comprehensive performance indicators with tooltips
- **Status Indicators**: Smart color-coding and status text based on metric thresholds
- **Detailed Explanations**: Contextual information for each metric

#### **2. Risk Analytics**
- **Risk Distribution**: Interactive pie charts showing risk component breakdown
- **VaR Analysis**: Historical and parametric Value-at-Risk calculations
- **Tail Risk Assessment**: Conditional VaR and extreme scenario analysis
- **Risk Summary**: Comprehensive risk analysis with actionable insights

#### **3. Asset Allocation**
- **Interactive Charts**: Both pie and bar chart visualizations
- **Detailed Breakdown**: Comprehensive asset table with allocation bars
- **Diversification Analysis**: Automatic scoring and recommendations
- **Asset Class Mapping**: Intelligent categorization and analysis

#### **4. Efficient Frontier**
- **Optimization Analysis**: Modern Portfolio Theory implementation
- **Special Portfolios**: Maximum Sharpe Ratio, Global Minimum Volatility
- **Interactive Scatter Plot**: Risk-return visualization with portfolio positioning
- **Efficiency Scoring**: Portfolio optimization assessment and recommendations

#### **5. Monte Carlo Simulation**
- **1000+ Scenarios**: Comprehensive simulation with statistical analysis
- **Path Visualization**: Sample simulation paths with mean trajectory
- **Distribution Analysis**: Final return distribution with percentile analysis
- **Risk Assessment**: Probability analysis and confidence scoring
- **Scenario Planning**: Best/worst case analysis with actionable insights

#### **6. CPPI Strategy Analysis**
- **Dynamic Strategy**: Constant Proportion Portfolio Insurance implementation
- **Performance Comparison**: CPPI vs Buy-and-Hold with outperformance metrics
- **Risk Budget Tracking**: Dynamic allocation and risk management visualization
- **Drawdown Analysis**: Comparative downside protection assessment
- **Strategy Mechanics**: Detailed explanation of CPPI parameters and benefits

### **Technical Features**

#### **Backend (FastAPI)**
- **High-Performance API**: FastAPI with async support and automatic documentation
- **Real Market Data**: Integration with yfinance for live data feeds
- **Comprehensive Analytics**: NumPy, SciPy, and Pandas for financial calculations
- **Robust Error Handling**: Graceful fallback to mock data when needed
- **Professional Endpoints**: RESTful API design with comprehensive data models

#### **Frontend (React + Vite)**
- **Modern React**: Hooks-based architecture with functional components
- **Interactive Charts**: Recharts integration with custom tooltips and legends
- **Dark Mode Support**: Complete theme switching with persistence
- **Responsive Design**: Mobile-first design that works on all devices
- **Performance Optimized**: Lazy loading and efficient state management

#### **Advanced Calculations**
- **Portfolio Theory**: Mean-variance optimization and efficient frontier calculation
- **Risk Management**: VaR, CVaR, and comprehensive risk metrics
- **Monte Carlo**: Geometric Brownian Motion simulation with statistical analysis
- **CPPI Strategy**: Dynamic portfolio insurance with floor protection
- **Performance Attribution**: Asset-level contribution and risk analysis

## 📊 Dashboard Sections

### 1. **Performance Overview**
- Annual return, volatility, and risk-adjusted metrics
- Individual asset performance visualization
- Smart metric interpretation with status indicators
- Comprehensive tooltips explaining each metric

### 2. **Risk Analytics**
- Value-at-Risk analysis (95% and 99% confidence levels)
- Expected Shortfall (Conditional VaR) calculation
- Downside deviation and semivariance analysis
- Risk distribution visualization and assessment

### 3. **Asset Allocation**
- Interactive pie chart showing portfolio composition
- Bar chart displaying asset values and weights
- Detailed allocation table with visual allocation bars
- Diversification scoring and improvement recommendations

### 4. **Efficient Frontier**
- Risk-return optimization visualization
- Maximum Sharpe Ratio and Global Minimum Volatility portfolios
- Current portfolio positioning analysis
- Efficiency scoring and optimization recommendations

### 5. **Monte Carlo Simulation**
- 1000-scenario simulation with path visualization
- Final return distribution analysis
- Percentile-based risk assessment
- Success probability calculation and confidence scoring

### 6. **CPPI Strategy**
- Dynamic portfolio insurance strategy analysis
- Performance comparison with static buy-and-hold
- Risk budget evolution and allocation dynamics
- Drawdown comparison and downside protection assessment

## 🛠️ Technology Stack

### Backend
- **FastAPI**: Modern Python web framework with automatic API documentation
- **NumPy**: Numerical computing for portfolio calculations
- **Pandas**: Data manipulation and time series analysis
- **SciPy**: Statistical functions and optimization algorithms
- **yfinance**: Real-time market data integration
- **Matplotlib/Seaborn**: Chart generation capabilities

### Frontend
- **React 18**: Latest React with hooks and functional components
- **Vite**: Fast build tool with hot module replacement
- **Tailwind CSS**: Utility-first styling with dark mode support
- **Recharts**: Professional chart library with interactive features
- **Axios**: HTTP client for API communication
- **Lucide React**: Modern icon library

### Development
- **TypeScript Support**: Type safety for better development experience
- **ESLint**: Code quality and consistency enforcement
- **Hot Reload**: Instant updates during development
- **Docker Support**: Containerized deployment ready

## 🚀 Quick Start

### Using Docker (Recommended)

1. **Start the application:**
   ```bash
   cd portfolio-dashboard
   docker-compose up -d
   ```

2. **Access the dashboard:**
   - Frontend: http://localhost
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Local Development

#### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at http://localhost:5173

## 📊 API Endpoints

### Core Endpoints
- `GET /api/portfolio` - Complete portfolio data with all analytics
- `GET /api/performance` - Performance metrics only
- `GET /api/risk` - Risk analytics data
- `GET /api/allocation` - Asset allocation information
- `GET /api/efficient-frontier` - Efficient frontier data
- `GET /api/monte-carlo` - Monte Carlo simulation results
- `GET /api/cppi` - CPPI strategy analysis
- `GET /api/individual-performance` - Individual asset metrics

### Documentation
- Full API documentation available at http://localhost:8000/docs
- Interactive API testing interface included
- Comprehensive request/response schemas

## 🎯 Key Features Explained

### **Real-Time Market Integration**
The dashboard connects to Yahoo Finance to fetch live market data for all portfolio assets. This ensures that all analytics and visualizations reflect current market conditions, providing relevant and actionable insights.

### **Professional Risk Management**
Advanced risk analytics including Value-at-Risk (VaR) calculations, Expected Shortfall analysis, and comprehensive downside risk assessment. The system provides both historical and parametric risk models for robust analysis.

### **Portfolio Optimization**
Implementation of Modern Portfolio Theory with efficient frontier analysis, optimal portfolio identification, and rebalancing recommendations based on risk-return optimization.

### **Monte Carlo Simulation**
Comprehensive scenario analysis using 1000+ simulations to project potential portfolio outcomes, assess success probabilities, and quantify uncertainty in investment returns.

### **Dynamic Strategy Analysis**
CPPI (Constant Proportion Portfolio Insurance) strategy implementation with real-time comparison against static buy-and-hold approaches, demonstrating the benefits of dynamic risk management.

## 🔧 Configuration

### Portfolio Configuration
Edit `backend/main.py` to modify the portfolio:

```python
PORTFOLIO_CONFIG = {
    'name': "Your Portfolio Name",
    'initial_value': 1000000,
    'asset_allocation': {
        'AAPL': 0.20,  # 20% Apple
        'GOOGL': 0.15, # 15% Google
        # Add more assets...
    }
}
```

### Environment Variables
Create `.env` files for configuration:

#### Backend (.env)
```env
ENVIRONMENT=development
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

#### Frontend (.env)
```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_APP_TITLE=Portfolio Dashboard
```

## 📱 Responsive Design

The dashboard is fully responsive and works seamlessly across:
- **Desktop**: Full feature set with side-by-side charts
- **Tablet**: Optimized layouts with stacked visualizations
- **Mobile**: Touch-friendly interface with collapsible sections

## 🎨 Dark Mode Support

Complete dark mode implementation with:
- System preference detection
- Manual toggle option
- Persistent theme selection
- Optimized colors for both light and dark themes

## 🚢 Deployment

### Production Deployment

1. **Configure environment variables for production**
2. **Set up reverse proxy (nginx/traefik)**
3. **Configure SSL certificates**
4. **Deploy using Docker Compose:**

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Cloud Deployment Options
- **AWS**: ECS/EKS with RDS for data persistence
- **Google Cloud**: Cloud Run with Cloud SQL
- **Azure**: Container Instances with Azure Database
- **DigitalOcean**: App Platform with managed databases

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest tests/ -v
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Integration Tests
```bash
# Test API endpoints
curl http://localhost:8000/api/portfolio
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Commit your changes: `git commit -m 'Add amazing feature'`
5. Push to the branch: `git push origin feature/amazing-feature`
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Troubleshooting

### Common Issues

1. **Backend not starting**
   - Check Python version (3.11+ required)
   - Verify all dependencies are installed
   - Check port 8000 availability

2. **Frontend build errors**
   - Ensure Node.js 18+ is installed
   - Clear npm cache: `npm cache clean --force`
   - Delete node_modules and reinstall

3. **Market data not loading**
   - Check internet connection
   - Verify yfinance is properly installed
   - Check for API rate limiting

4. **Charts not displaying**
   - Verify Recharts is properly installed
   - Check browser console for JavaScript errors
   - Ensure data format matches expected schema

### Performance Optimization

- Enable gzip compression for production
- Implement Redis caching for market data
- Use CDN for static assets
- Configure database connection pooling

## 🎉 Features Roadmap

- [ ] **Real-time WebSocket updates**
- [ ] **Advanced backtesting engine**
- [ ] **Custom benchmark comparisons**
- [ ] **Alert system for portfolio events**
- [ ] **PDF report generation**
- [ ] **Multi-currency support**
- [ ] **Options and derivatives analysis**
- [ ] **ESG scoring integration**

---

**Built with ❤️ using React, FastAPI, and modern financial analytics**

For support and questions, please check the API documentation at http://localhost:8000/docs or review the troubleshooting section above.
