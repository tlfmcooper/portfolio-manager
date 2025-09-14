#!/usr/bin/env python3
"""
Portfolio Manager - Cash Position Example

This example demonstrates creating a portfolio with some cash allocation.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from portfolio_manager import Portfolio, YFinanceProvider
from portfolio_manager.analytics.performance import PerformanceAnalytics
from portfolio_manager.analytics.risk import RiskAnalytics


def main():
    print("=== Portfolio with Cash Position Example ===")
    
    # Set up data provider
    print("\n1. Setting up data provider...")
    provider = YFinanceProvider()
    
    # Fetch sample assets
    symbols = ['AAPL', 'GOOGL', 'MSFT']
    print(f"2. Fetching data for: {', '.join(symbols)}")
    
    assets = provider.get_multiple_assets(symbols)
    print(f"   Successfully loaded {len(assets)} assets")
    
    if not assets:
        print("   ERROR: No assets loaded successfully!")
        return
    
    # Create portfolio with 80% stocks, 20% cash
    print("\n3. Creating portfolio (80% stocks, 20% cash)...")
    portfolio = Portfolio(name="Conservative Tech Portfolio")
    
    # Allocate only 80% to stocks (keeping 20% in cash)
    stock_allocation = 0.80
    weights_per_stock = stock_allocation / len(assets)  # Divide 80% among stocks
    
    for asset in assets:
        portfolio.add_asset(asset.symbol, asset, weights_per_stock)
        print(f"   Added {asset.symbol}: {weights_per_stock:.1%}")
    
    # Calculate and display cash position
    total_stock_weight = sum(portfolio.weights.values())
    cash_position = 1.0 - total_stock_weight
    
    print(f"   Cash position: {cash_position:.1%}")
    print(f"   Total allocation: {total_stock_weight + cash_position:.1%}")
    
    # Portfolio summary
    print("\n4. Portfolio Summary:")
    summary = portfolio.summary()
    for key, value in summary.items():
        if key == 'total_weight':
            print(f"   {key}: {value:.1%} (stocks)")
            print(f"   cash_position: {cash_position:.1%}")
        elif key != 'weights':
            print(f"   {key}: {value}")
    
    # Performance analysis
    print("\n5. Performance Analysis:")
    try:
        perf = PerformanceAnalytics(portfolio)
        
        total_return = perf.total_return()
        annual_return = perf.annualized_return()
        volatility = perf.volatility()
        sharpe_ratio = perf.sharpe_ratio()
        
        print(f"   Stock Portion Return: {total_return:.2%}")
        print(f"   Stock Portion Annualized Return: {annual_return:.2%}")
        print(f"   Stock Portion Volatility: {volatility:.2%}")
        print(f"   Stock Portion Sharpe Ratio: {sharpe_ratio:.2f}")
        
        # Calculate blended portfolio metrics (stocks + cash)
        # Assuming cash returns 0% (or you could use risk-free rate)
        cash_return = 0.0
        blended_return = total_return * total_stock_weight + cash_return * cash_position
        blended_annual = annual_return * total_stock_weight + cash_return * cash_position
        blended_volatility = volatility * total_stock_weight  # Cash has no volatility
        
        print(f"\n   Blended Portfolio Metrics (including cash):")
        print(f"   Total Portfolio Return: {blended_return:.2%}")
        print(f"   Total Portfolio Annual Return: {blended_annual:.2%}")
        print(f"   Total Portfolio Volatility: {blended_volatility:.2%}")
        
    except Exception as e:
        print(f"   Error in performance analysis: {e}")
    
    # Risk analysis
    print("\n6. Risk Analysis:")
    try:
        risk = RiskAnalytics(portfolio)
        
        portfolio_var = risk.portfolio_variance()
        portfolio_vol = risk.portfolio_volatility()
        
        print(f"   Stock Portion Variance: {portfolio_var:.4f}")
        print(f"   Stock Portion Volatility: {portfolio_vol:.2%}")
        
        # Show correlation matrix
        corr_matrix = risk.correlation_matrix()
        if not corr_matrix.empty:
            print(f"\n   Stock Correlation Matrix:")
            print(corr_matrix.round(3).to_string())
        
    except Exception as e:
        print(f"   Error in risk analysis: {e}")
    
    # Individual asset analysis
    print("\n7. Individual Asset Analysis:")
    try:
        for asset in assets:
            perf = PerformanceAnalytics(Portfolio(name="temp").add_asset(asset.symbol, asset, 1.0))
            current_price = asset.price_data['Close'].iloc[-1]
            volatility = perf.volatility()
            sharpe = perf.sharpe_ratio()
            
            print(f"   {asset.symbol}:")
            print(f"     Current Price: ${current_price:.2f}")
            print(f"     Portfolio Weight: {weights_per_stock:.1%}")
            print(f"     Volatility: {volatility:.2%}")
            print(f"     Sharpe Ratio: {sharpe:.2f}")
    except Exception as e:
        print(f"   Error in asset analysis: {e}")
    
    print(f"\n=== Cash Position Benefits ===")
    print(f"• Lower portfolio volatility: {blended_volatility:.2%} vs {volatility:.2%}")
    print(f"• Reduced downside risk during market crashes")
    print(f"• Flexibility to buy opportunities when they arise")
    print(f"• Peace of mind during volatile periods")
    
    print("\n=== Example Complete ===")


if __name__ == "__main__":
    main()
