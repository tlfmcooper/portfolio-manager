"""
Basic Portfolio Example

This example demonstrates how to create a simple portfolio,
add assets, and perform basic analysis.
"""

from datetime import date, timedelta
import sys
import os

# Add the src directory to the path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from portfolio_manager import Portfolio, YFinanceProvider, PerformanceAnalytics, RiskAnalytics


def main():
    """Main example function."""
    print("=== Portfolio Manager Basic Example ===\n")
    
    # Create data provider
    print("1. Setting up data provider...")
    provider = YFinanceProvider()
    
    # Define the assets we want
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN']
    
    print(f"2. Fetching data for: {', '.join(symbols)}")
    
    # Get assets with 1 year of data
    end_date = date.today()
    start_date = end_date - timedelta(days=365)
    
    try:
        assets = provider.get_multiple_assets(symbols, start_date, end_date)
        print(f"   Successfully loaded {len(assets)} assets")
    except Exception as e:
        print(f"   Error loading assets: {e}")
        return
    
    # Create portfolio
    print("\n3. Creating portfolio...")
    portfolio = Portfolio(name="Tech Giants Portfolio")
    
    # Add assets with equal weights
    weights = [0.25, 0.25, 0.25, 0.25]
    
    for asset, weight in zip(assets, weights):
        portfolio.add_asset(asset.symbol, asset, weight)
        print(f"   Added {asset.symbol}: {weight:.1%}")
    
    # Portfolio summary
    print("\n4. Portfolio Summary:")
    summary = portfolio.summary()
    for key, value in summary.items():
        if key != 'weights':
            print(f"   {key}: {value}")
    
    # Performance analysis
    print("\n5. Performance Analysis:")
    try:
        perf = PerformanceAnalytics(portfolio)
        
        total_return = perf.total_return()
        annual_return = perf.annualized_return()
        volatility = perf.volatility()
        sharpe_ratio = perf.sharpe_ratio()
        
        print(f"   Total Return: {total_return:.2%}")
        print(f"   Annualized Return: {annual_return:.2%}")
        print(f"   Volatility: {volatility:.2%}")
        print(f"   Sharpe Ratio: {sharpe_ratio:.2f}")
        
    except Exception as e:
        print(f"   Error in performance analysis: {e}")
    
    # Risk analysis
    print("\n6. Risk Analysis:")
    try:
        risk = RiskAnalytics(portfolio)
        
        corr_matrix = risk.correlation_matrix()
        portfolio_var = risk.portfolio_variance()
        
        print(f"   Portfolio Variance: {portfolio_var:.4f}")
        print(f"   Portfolio Volatility: {portfolio_var**0.5:.2%}")
        
        print("\n   Correlation Matrix:")
        if not corr_matrix.empty:
            print(corr_matrix.round(3))
        else:
            print("   No correlation data available")
            
    except Exception as e:
        print(f"   Error in risk analysis: {e}")
    
    # Individual asset analysis
    print("\n7. Individual Asset Analysis:")
    for symbol, asset in portfolio.assets.items():
        try:
            current_price = asset.get_current_price()
            volatility = asset.get_volatility()
            sharpe = asset.get_sharpe_ratio()
            
            print(f"   {symbol}:")
            print(f"     Current Price: ${current_price:.2f}")
            print(f"     Volatility: {volatility:.2%}")
            print(f"     Sharpe Ratio: {sharpe:.2f}")
            
        except Exception as e:
            print(f"     Error analyzing {symbol}: {e}")
    
    print("\n=== Example Complete ===")


if __name__ == "__main__":
    main()
