# Portfolio Manager

A comprehensive Python package for portfolio management and analysis, built on modern portfolio theory and EDHEC Risk Kit methodology.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Features

- **Portfolio Construction**: Build and manage investment portfolios with multiple assets
- **Risk Analytics**: Comprehensive risk analysis including VaR, correlation analysis, and stress testing
- **Performance Analytics**: Calculate returns, Sharpe ratios, drawdowns, and other performance metrics
- **Portfolio Optimization**: Modern portfolio theory optimization including mean-variance, risk parity, and Black-Litterman
- **Data Integration**: Seamless integration with Yahoo Finance and other data providers
- **Legacy Support**: Backward compatibility with EDHEC Risk Kit functions

## Installation

### Using UV (Recommended)

```bash
uv add portfolio-manager
```

### Using pip

```bash
pip install portfolio-manager
```

### Development Installation

```bash
git clone https://github.com/alikone/portfolio-manager.git
cd portfolio-manager
uv sync --all-extras
```

## Quick Start

### Basic Portfolio Creation

```python
from portfolio_manager import Portfolio, YFinanceProvider
from datetime import date, timedelta

# Create data provider
provider = YFinanceProvider()

# Create assets
assets = provider.get_multiple_assets(
    ['AAPL', 'GOOGL', 'MSFT', 'TSLA'],
    start_date=date.today() - timedelta(days=365)
)

# Create portfolio
portfolio = Portfolio(name="Tech Portfolio")

# Add assets with weights
portfolio.add_asset('AAPL', assets[0], 0.3)
portfolio.add_asset('GOOGL', assets[1], 0.25)
portfolio.add_asset('MSFT', assets[2], 0.25)
portfolio.add_asset('TSLA', assets[3], 0.2)

print(portfolio.summary())
```

### Performance Analysis

```python
from portfolio_manager import PerformanceAnalytics

# Get performance analytics
perf = PerformanceAnalytics(portfolio)

# Calculate key metrics
total_return = perf.total_return()
annual_return = perf.annualized_return()
volatility = perf.volatility()
sharpe_ratio = perf.sharpe_ratio()

print(f"Total Return: {total_return:.2%}")
print(f"Annual Return: {annual_return:.2%}")
print(f"Volatility: {volatility:.2%}")
print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
```

### Risk Analysis

```python
from portfolio_manager import RiskAnalytics

# Get risk analytics
risk = RiskAnalytics(portfolio)

# Calculate risk metrics
correlation_matrix = risk.correlation_matrix()
portfolio_var = risk.portfolio_variance()

print("Correlation Matrix:")
print(correlation_matrix)
print(f"Portfolio Variance: {portfolio_var:.4f}")
```

### Portfolio Optimization

```python
from portfolio_manager import PortfolioOptimizer

# Optimize portfolio
optimizer = PortfolioOptimizer(assets)

# Mean-variance optimization
optimal_weights = optimizer.mean_variance_optimization()

print("Optimal Weights:")
for symbol, weight in optimal_weights['weights'].items():
    print(f"{symbol}: {weight:.2%}")
```

## Documentation

Full documentation is available at [portfolio-manager.readthedocs.io](https://portfolio-manager.readthedocs.io)

### Examples

- [Basic Usage](docs/notebooks/basic_usage.ipynb)
- [Portfolio Optimization](docs/notebooks/portfolio_optimization.ipynb) 
- [Risk Analysis](docs/notebooks/risk_analysis.ipynb)

## Legacy EDHEC Functions

The package includes all original EDHEC Risk Kit functions for backward compatibility:

```python
from portfolio_manager.legacy import risk_functions

# Load EDHEC data
hfi_returns = risk_functions.get_hfi_returns()
ind_returns = risk_functions.get_ind_returns()

# Calculate risk metrics
skew = risk_functions.skewness(hfi_returns)
kurt = risk_functions.kurtosis(hfi_returns)
```

## Project Structure

```
portfolio-manager/
├── src/portfolio_manager/       # Main package
│   ├── core/                   # Core classes (Portfolio, Asset)
│   ├── analytics/              # Analytics modules
│   ├── data/                   # Data providers
│   ├── legacy/                 # Legacy EDHEC functions
│   └── utils/                  # Utilities
├── tests/                      # Test suite
├── docs/                       # Documentation
├── examples/                   # Example scripts
└── data/                       # Sample data files
```

## Development

### Setting up Development Environment

```bash
# Clone repository
git clone https://github.com/alikone/portfolio-manager.git
cd portfolio-manager

# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=portfolio_manager --cov-report=html

# Run specific test file
uv run pytest tests/test_portfolio.py
```

### Code Quality

```bash
# Format code
uv run black src/ tests/

# Sort imports
uv run isort src/ tests/

# Lint code
uv run flake8 src/ tests/

# Type checking
uv run mypy src/
```

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Based on EDHEC Risk Kit methodology
- Built with modern Python packaging best practices
- Inspired by quantitative finance research and industry practices

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes.

## Support

- 📚 [Documentation](https://portfolio-manager.readthedocs.io)
- 🐛 [Issue Tracker](https://github.com/alikone/portfolio-manager/issues)
- 💬 [Discussions](https://github.com/alikone/portfolio-manager/discussions)
