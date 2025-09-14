"""
Advanced Portfolio Manager Features
==================================

This script demonstrates advanced portfolio management techniques including:
- Advanced portfolio optimization
- Risk analysis and attribution
- Performance attribution
- Advanced visualization
"""

# Standard library imports
import sys
import os
import io
from pathlib import Path
from datetime import datetime, timedelta
import warnings

# Set console encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Third-party imports
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.dates as mdates
from scipy import stats
import seaborn as sns

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Add src to path
project_root = Path.cwd().parent if 'notebooks' in str(Path.cwd()) else Path.cwd()
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))

# Import portfolio manager components
try:
    from portfolio_manager import Portfolio, YFinanceProvider
    from portfolio_manager.core.asset import Asset, AssetType
    from portfolio_manager.analytics.performance import PerformanceAnalytics
    from portfolio_manager.analytics.risk import RiskAnalytics
    from portfolio_manager.analytics.optimization import PortfolioOptimizer
    print("[OK] Portfolio Manager imported successfully!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"Current working directory: {Path.cwd()}")
    print(f"Src exists: {src_path.exists()}")
    raise  # Re-raise to prevent further execution

# Set up plotting
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 12
plt.rcParams['figure.titlesize'] = 16
plt.rcParams['axes.titlesize'] = 14

# Constants
ASSET_UNIVERSE = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',  # Tech
    'JPM', 'BAC', 'GS', 'MS', 'C',            # Financials
    'JNJ', 'PFE', 'MRK', 'UNH', 'ABT',        # Healthcare
    'XOM', 'CVX', 'COP', 'BP', 'TOT',         # Energy
    'PG', 'KO', 'PEP', 'WMT', 'COST'          # Consumer Staples
]

# Initialize data provider
provider = YFinanceProvider()

# Helper functions
def ensure_naive_datetime(dt):
    """Convert datetime to timezone-naive if it's timezone-aware."""
    if dt is None:
        return None
    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt

def load_assets(symbols, start_date=None, end_date=None):
    """Load asset data from YFinance with consistent timezone handling."""
    print(f"Loading data for {len(symbols)} assets...")
    
    # Ensure dates are timezone-naive
    start_date = ensure_naive_datetime(start_date)
    end_date = ensure_naive_datetime(end_date)
    
    # Use a dictionary to store assets with symbols as keys
    assets = {}
    for symbol in symbols:
        try:
            # Get historical data
            data = provider.get_price_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                interval='1d'
            )
            
            if data is not None and not data.empty:
                # Ensure timezone-naive index
                if data.index.tz is not None:
                    data.index = data.index.tz_convert(None)
                
                # Calculate returns and add to the DataFrame
                if 'Close' in data.columns:
                    data['Returns'] = data['Close'].pct_change().dropna()
                
                # Create asset
                asset = Asset(
                    symbol=symbol,
                    name=symbol,
                    asset_type=AssetType.STOCK,
                    currency="USD"
                )
                
                # Set price data (including returns)
                asset.set_price_data(data)
                assets[symbol] = asset
                print(f"  - {symbol}: Loaded {len(data)} data points")
                
                # Debug: Verify returns calculation
                if 'Returns' in data.columns:
                    print(f"     Returns: {len(data['Returns'].dropna())} points "
                          f"(first: {data['Returns'].iloc[1]:.6f}, "
                          f"last: {data['Returns'].iloc[-1]:.6f})")
            else:
                print(f"  - {symbol}: No data available")
                
        except Exception as e:
            print(f"  - {symbol}: Error loading data - {str(e)}")
            import traceback
            traceback.print_exc()
    
    if not assets:
        print("Error: No assets could be loaded. Please check your internet connection and try again.")
        return None
    
    print(f"[OK] Successfully loaded {len(assets)} assets")
    return assets

def calculate_max_drawdown(returns_series):
    """Calculate maximum drawdown from a return series."""
    if returns_series.empty:
        return 0.0
    cum_returns = (1 + returns_series).cumprod()
    rolling_max = cum_returns.cummax()
    drawdowns = (cum_returns - rolling_max) / rolling_max
    return drawdowns.min()

def ensure_portfolio_returns(portfolio):
    """Ensure the portfolio has valid price data and returns."""
    for symbol, asset in portfolio.assets.items():
        if hasattr(asset, 'price_data') and asset.price_data is not None:
            # Ensure we have 'Close' prices
            if 'Close' not in asset.price_data.columns:
                print(f"  - {symbol}: No 'Close' prices found in data")
                continue
                
            # Calculate returns if not already present
            if 'Returns' not in asset.price_data.columns:
                try:
                    asset.price_data['Returns'] = asset.price_data['Close'].pct_change().dropna()
                    print(f"  - {symbol}: Calculated {len(asset.price_data['Returns'])} returns")
                except Exception as e:
                    print(f"  - {symbol}: Error calculating returns - {str(e)}")
    return portfolio

def create_portfolio(assets_dict, name="Advanced Portfolio"):
    """Create an equally weighted portfolio from assets dictionary."""
    portfolio = Portfolio(name=name)
    weight = 1.0 / len(assets_dict) if assets_dict else 0
    
    print(f"\nCreating portfolio '{name}' with {len(assets_dict)} assets:")
    for symbol, asset in assets_dict.items():
        try:
            portfolio.add_asset(symbol, asset, weight)
            print(f"  - {symbol}: {weight:.1%}")
        except Exception as e:
            print(f"  - {symbol}: Error adding to portfolio - {str(e)}")
    
    # Verify portfolio has assets before returning
    if len(portfolio.assets) == 0:
        raise ValueError("No assets were successfully added to the portfolio")
    
    # Ensure all assets have proper returns calculated
    portfolio = ensure_portfolio_returns(portfolio)
    
    return portfolio

def plot_efficient_frontier(optimizer, risk_free_rate=0.02, n_points=20):
    """Plot the efficient frontier from an optimizer."""
    try:
        # Get expected returns and covariance matrix
        optimizer._prepare_data()
        expected_returns = optimizer._expected_returns
        cov_matrix = optimizer._cov_matrix
        
        # Ensure we have valid data
        if expected_returns is None or cov_matrix is None:
            print("Error: Missing expected returns or covariance matrix")
            return
            
        # Check if we have valid data points
        if len(expected_returns) == 0 or cov_matrix.size == 0:
            print("Error: No valid data points for efficient frontier")
            return
            
        # Calculate portfolio statistics for different weights
        returns = []
        volatilities = []
        weights = []
        
        # Generate random portfolios
        for _ in range(n_points):
            # Generate random weights
            w = np.random.random(len(expected_returns))
            w /= np.sum(w)  # Ensure weights sum to 1
            
            try:
                # Calculate portfolio return and volatility
                port_return = np.sum(w * expected_returns) * 252  # Annualize
                port_vol = np.sqrt(np.dot(w.T, np.dot(cov_matrix * 252, w)))  # Annualize
                
                # Only add if we have valid values
                if not np.isnan(port_return) and not np.isnan(port_vol):
                    returns.append(port_return)
                    volatilities.append(port_vol)
                    weights.append(w)
            except Exception as e:
                print(f"  - Warning: Error calculating portfolio metrics: {str(e)}")
                continue
        
        if not returns or not volatilities:
            print("Error: No valid portfolios could be calculated")
            return
        
        # Calculate Sharpe ratios
        sharpe_ratios = (np.array(returns) - risk_free_rate) / np.array(volatilities)
        
        # Plot the efficient frontier
        plt.figure(figsize=(12, 8))
        scatter = plt.scatter(volatilities, returns, c=sharpe_ratios, 
                   marker='o', cmap='viridis', alpha=0.7)
        
        # Add color bar and labels
        cbar = plt.colorbar(scatter)
        cbar.set_label('Sharpe Ratio')
        plt.xlabel('Volatility (Annualized)')
        plt.ylabel('Return (Annualized)')
        plt.title('Efficient Frontier')
        plt.grid(True, alpha=0.3)
        
        # Add maximum Sharpe ratio portfolio
        max_sharpe_idx = np.argmax(sharpe_ratios)
        plt.scatter(volatilities[max_sharpe_idx], returns[max_sharpe_idx], 
                   marker='*', color='r', s=200, label='Max Sharpe Ratio')
        
        plt.legend()
        plt.tight_layout()
        plt.show()
        
    except Exception as e:
        print(f"Error plotting efficient frontier: {str(e)}")

def main():
    """Main function to demonstrate advanced features."""
    try:
        # Set date range (last 5 years)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5*365)
        
        # Convert to timezone-naive dates for compatibility
        end_date = ensure_naive_datetime(end_date)
        start_date = ensure_naive_datetime(start_date)
        
        print(f"Date range: {start_date.date()} to {end_date.date()}")
        
        # Load assets with error handling
        assets = load_assets(ASSET_UNIVERSE, start_date, end_date)
        if not assets:
            print("Error: No assets could be loaded. Please check your internet connection and try again.")
            return
            
        # Create portfolio
        portfolio = create_portfolio(assets)
        
        # Initialize analytics
        risk_analytics = RiskAnalytics(portfolio)
        perf_analytics = PerformanceAnalytics(portfolio)
        
        # 1. Advanced Optimization
        print("\n1. Running Advanced Portfolio Optimization...")
        try:
            # Ensure dates are timezone-naive for the optimizer
            opt_start = start_date.replace(tzinfo=None) if start_date.tzinfo else start_date
            opt_end = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date
            
            print(f"  1.0. Initializing optimizer with {len(assets)} assets...")
            # Get the actual Asset objects from the portfolio
            asset_objects = list(portfolio.assets.values())
            optimizer = PortfolioOptimizer(asset_objects, opt_start, opt_end)
            
            # 1.1 Mean-Variance Optimization
            print("  1.1. Mean-Variance Optimization")
            try:
                mvo_result = optimizer.mean_variance_optimization()
                if mvo_result and 'weights' in mvo_result:
                    mvo_weights = mvo_result['weights']
                    print(f"      Optimal weights calculated for {len(mvo_weights)} assets")
                else:
                    print("      Warning: No optimal weights returned from MVO")
            except Exception as e:
                print(f"      Error in Mean-Variance Optimization: {str(e)}")
            
            # 1.2 Risk Parity
            print("  1.2. Risk Parity Allocation")
            try:
                rp_result = optimizer.risk_parity_optimization()
                if rp_result and 'weights' in rp_result:
                    rp_weights = rp_result['weights']
                    print(f"      Risk parity weights calculated for {len(rp_weights)} assets")
                else:
                    print("      Warning: No risk parity weights returned")
            except Exception as e:
                print(f"      Error in Risk Parity Optimization: {str(e)}")
            
            # 1.3 Efficient Frontier
            print("  1.3. Plotting Efficient Frontier")
            try:
                plot_efficient_frontier(optimizer)
            except Exception as e:
                print(f"      Error plotting efficient frontier: {str(e)}")
            
        except Exception as e:
            print(f"Error during portfolio optimization: {str(e)}")
            print("Continuing with other analyses...")
        
        # 2. Advanced Risk Analysis
        print("\n2. Running Advanced Risk Analysis...")
        try:
            # 2.1 Correlation Heatmap
            print("  2.1. Asset Correlation Matrix")
            try:
                corr_matrix = risk_analytics.correlation_matrix()
                
                plt.figure(figsize=(14, 12))
                sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', 
                          center=0, fmt='.2f', linewidths=0.5)
                plt.title('Asset Correlation Matrix')
                plt.tight_layout()
                plt.show()
            except Exception as e:
                print(f"      Error creating correlation matrix: {str(e)}")
            
            # 2.2 Risk Decomposition
            print("  2.2. Risk Decomposition")
            try:
                risk_contrib = risk_analytics.risk_contribution()
                
                if isinstance(risk_contrib, dict):
                    risk_df = pd.DataFrame({
                        'Asset': list(risk_contrib.keys()),
                        'Risk Contribution': list(risk_contrib.values())
                    })
                    
                    # Sort by risk contribution
                    risk_df = risk_df.sort_values('Risk Contribution', ascending=False)
                    
                    plt.figure(figsize=(14, 8))
                    sns.barplot(data=risk_df, x='Asset', y='Risk Contribution', 
                               palette='viridis')
                    plt.title('Risk Contribution by Asset')
                    plt.ylabel('Risk Contribution')
                    plt.xticks(rotation=45, ha='right')
                    plt.tight_layout()
                    plt.show()
                    
                    # Print top 5 risk contributors
                    print("\nTop 5 Risk Contributors:")
                    print(risk_df.head().to_string(index=False))
                else:
                    print("      Warning: Risk contribution data is not in the expected format")
                    
            except Exception as e:
                print(f"      Error in risk decomposition: {str(e)}")
            
        except Exception as e:
            print(f"Error during risk analysis: {str(e)}")
            print("Continuing with performance analysis...")
        
            # 3.1 Performance Summary
            print("  3.1. Performance Summary")
            
            # Debug: Print portfolio assets and weights
            print("\nPortfolio Assets and Weights:")
            for symbol, weight in portfolio.weights.items():
                asset = portfolio.assets[symbol]
                has_data = hasattr(asset, 'price_data') and asset.price_data is not None
                has_returns = has_data and 'Returns' in asset.price_data.columns
                print(f"  - {symbol}: {weight:.1%} | Has data: {has_data} | Has returns: {has_returns}")
            
            # Get portfolio returns for debugging
            print("\n=== DEBUG: Portfolio Returns Calculation ===")
            print(f"Number of assets in portfolio: {len(portfolio.assets)}")
            
            # First, verify each asset has returns data
            assets_with_returns = 0
            for symbol, asset in portfolio.assets.items():
                has_data = hasattr(asset, 'price_data') and asset.price_data is not None
                has_returns = has_data and 'Returns' in asset.price_data.columns
                weight = portfolio.weights.get(symbol, 0)
                print(f"  - {symbol}: weight={weight:.2%}, has_data={has_data}, has_returns={has_returns}")
                if has_returns:
                    print(f"     Returns count: {len(asset.price_data['Returns'])}, "
                          f"First: {asset.price_data['Returns'].iloc[0]:.6f}, "
                          f"Last: {asset.price_data['Returns'].iloc[-1]:.6f}")
                    assets_with_returns += 1
            
            print(f"\nFound {assets_with_returns} assets with returns data")
            
            try:
                # Manually calculate portfolio returns as a fallback
                all_returns = []
                for symbol, asset in portfolio.assets.items():
                    if hasattr(asset, 'price_data') and 'Returns' in asset.price_data.columns:
                        weight = portfolio.weights.get(symbol, 0)
                        if weight > 0:
                            weighted_returns = asset.price_data['Returns'] * weight
                            all_returns.append(weighted_returns)
                
                if all_returns:
                    print(f"\nCombining returns from {len(all_returns)} assets...")
                    # Combine all asset returns
                    combined_returns = pd.concat(all_returns, axis=1).sum(axis=1).dropna()
                    
                    print("\n=== Portfolio Returns Summary ===")
                    print(f"Total return points: {len(combined_returns)}")
                    print(f"Date range: {combined_returns.index[0].date()} to {combined_returns.index[-1].date()}")
                    print(f"First 5 returns: {[f'{x:.6f}' for x in combined_returns.head().to_list()]}")
                    print(f"Last 5 returns:  {[f'{x:.6f}' for x in combined_returns.tail().to_list()]}")
                    
                    # Basic statistics
                    print("\nBasic Statistics:")
                    print(f"  Mean return: {combined_returns.mean():.6f}")
                    print(f"  Std dev:     {combined_returns.std():.6f}")
                    print(f"  Min:         {combined_returns.min():.6f}")
                    print(f"  Max:         {combined_returns.max():.6f}")
                    
                    # Calculate basic metrics manually
                    total_return = (1 + combined_returns).prod() - 1
                    annualized_return = (1 + total_return) ** (252/len(combined_returns)) - 1
                    volatility = combined_returns.std() * np.sqrt(252)
                    sharpe_ratio = np.sqrt(252) * combined_returns.mean() / (combined_returns.std() or 1e-6)  # Avoid division by zero
                    
                    # Create manual performance summary
                    perf_summary = {
                        'risk_metrics': {
                            'total_return': float(total_return),
                            'annualized_return': float(annualized_return),
                            'volatility': float(volatility),
                            'sharpe_ratio': float(sharpe_ratio),
                            'max_drawdown': float(calculate_max_drawdown(combined_returns)),
                            'var_95': float(combined_returns.quantile(0.05)),
                            'cvar_95': float(combined_returns[combined_returns <= combined_returns.quantile(0.05)].mean())
                        }
                    }
                    
                    # Store the combined returns for later use
                    portfolio_returns = combined_returns
                    
                else:
                    print("\nERROR: No valid returns data found in any asset")
                    perf_summary = {}
                    
            except Exception as e:
                print(f"\nERROR calculating portfolio returns: {str(e)}")
                import traceback
                traceback.print_exc()
                perf_summary = {}
            
            # Print available metrics for debugging
            print("\n=== Performance Metrics ===")
            if 'risk_metrics' in perf_summary:
                print("\nCalculated Metrics:")
                metrics = perf_summary['risk_metrics']
                print(f"  {'Metric':<20} | {'Value':>15}")
                print("-" * 40)
                print(f"  {'Total Return':<20} | {metrics['total_return']:>15.2%}")
                print(f"  {'Annualized Return':<20} | {metrics['annualized_return']:>15.2%}")
                print(f"  {'Volatility':<20} | {metrics['volatility']:>15.2%}")
                print(f"  {'Sharpe Ratio':<20} | {metrics['sharpe_ratio']:>15.2f}")
                print(f"  {'Max Drawdown':<20} | {metrics['max_drawdown']:>15.2%}")
                print(f"  {'Value at Risk (95%)':<20} | {metrics['var_95']:>15.2%}")
                print(f"  {'CVaR (95%)':<20} | {metrics['cvar_95']:>15.2%}")
            else:
                print("No performance metrics available")
            
            # 3.2 Drawdown Analysis
            print("\n  3.2. Drawdown Analysis")
            if portfolio_returns is not None and not portfolio_returns.empty:
                cum_returns = (1 + portfolio_returns).cumprod()
                running_max = cum_returns.cummax()
                drawdown_series = (cum_returns - running_max) / running_max
                
                plt.figure(figsize=(12, 6))
                plt.plot(drawdown_series.index, drawdown_series * 100, 'r-')
                plt.fill_between(drawdown_series.index, drawdown_series * 100, 0, 
                               color='red', alpha=0.2)
                
                # Calculate max drawdown info
                max_drawdown = drawdown_series.min()
                trough_idx = drawdown_series.idxmin()
                peak_idx = portfolio_returns[:trough_idx].idxmax()
                
                plt.title(f'Portfolio Drawdown (Max: {max_drawdown:.2%})')
                plt.ylabel('Drawdown (%)')
                plt.grid(True, alpha=0.3)
                
                # Mark the max drawdown period
                plt.axvspan(peak_idx, trough_idx, color='red', alpha=0.1)
                
                plt.tight_layout()
                plt.show()
            else:
                print("      No return data available for drawdown analysis")
                
        except Exception as e:
            print(f"Error during performance analysis: {str(e)}")
        
        print("\n[OK] Advanced analysis complete!")
        
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\n[ERROR] Analysis completed with errors.")

if __name__ == "__main__":
    main()
