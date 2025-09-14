Getting Started
===============

This guide will help you get started with Portfolio Manager quickly.

Installation
------------

Requirements
~~~~~~~~~~~~

* Python 3.9 or higher
* UV package manager (recommended) or pip

Install with UV
~~~~~~~~~~~~~~~

UV is the recommended package manager for Portfolio Manager::

    uv add portfolio-manager

Install with pip
~~~~~~~~~~~~~~~~

You can also install using pip::

    pip install portfolio-manager

Development Installation
~~~~~~~~~~~~~~~~~~~~~~~~

For development or to access the latest features::

    git clone https://github.com/alikone/portfolio-manager.git
    cd portfolio-manager
    uv sync --all-extras

Basic Concepts
--------------

Portfolio Manager is built around several core concepts:

Assets
~~~~~~

An :class:`~portfolio_manager.core.asset.Asset` represents a financial instrument:

.. code-block:: python

    from portfolio_manager.core.asset import Asset, AssetType

    asset = Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.STOCK,
        currency="USD"
    )

Portfolios
~~~~~~~~~~

A :class:`~portfolio_manager.core.portfolio.Portfolio` contains multiple assets with weights:

.. code-block:: python

    from portfolio_manager.core.portfolio import Portfolio

    portfolio = Portfolio(name="My Portfolio")
    portfolio.add_asset("AAPL", asset, 0.6)  # 60% weight

Data Providers
~~~~~~~~~~~~~~

Data providers fetch market data:

.. code-block:: python

    from portfolio_manager.data.providers import YFinanceProvider

    provider = YFinanceProvider()
    asset = provider.create_asset("AAPL")

Analytics
~~~~~~~~~

Analytics modules provide performance and risk analysis:

.. code-block:: python

    from portfolio_manager.analytics import PerformanceAnalytics, RiskAnalytics

    perf = PerformanceAnalytics(portfolio)
    risk = RiskAnalytics(portfolio)

    sharpe_ratio = perf.sharpe_ratio()
    volatility = risk.portfolio_variance()

First Example
-------------

Here's a complete example that creates a portfolio and analyzes it:

.. code-block:: python

    from portfolio_manager import Portfolio, YFinanceProvider
    from portfolio_manager.analytics import PerformanceAnalytics, RiskAnalytics
    from datetime import date, timedelta

    # 1. Create data provider
    provider = YFinanceProvider()

    # 2. Get some assets
    symbols = ['AAPL', 'GOOGL', 'MSFT']
    assets = provider.get_multiple_assets(
        symbols,
        start_date=date.today() - timedelta(days=365)
    )

    # 3. Create portfolio
    portfolio = Portfolio(name="Tech Portfolio")

    # 4. Add assets with equal weights
    for asset in assets:
        portfolio.add_asset(asset.symbol, asset, 1/len(assets))

    # 5. Analyze performance
    perf = PerformanceAnalytics(portfolio)
    risk = RiskAnalytics(portfolio)

    print(f"Annual Return: {perf.annualized_return():.2%}")
    print(f"Volatility: {perf.volatility():.2%}")
    print(f"Sharpe Ratio: {perf.sharpe_ratio():.2f}")
    print(f"Max Drawdown: {perf.max_drawdown()['max_drawdown']:.2%}")

Common Patterns
---------------

Loading Historical Data
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from datetime import date, timedelta

    # Get 2 years of data
    end_date = date.today()
    start_date = end_date - timedelta(days=730)

    assets = provider.get_multiple_assets(
        ['SPY', 'BND', 'VTI'], 
        start_date=start_date,
        end_date=end_date
    )

Creating Balanced Portfolios
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # 60/40 stock/bond portfolio
    portfolio = Portfolio(name="Balanced Portfolio")
    portfolio.add_asset('SPY', stock_etf, 0.6)
    portfolio.add_asset('BND', bond_etf, 0.4)

Performance Reporting
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    perf = PerformanceAnalytics(portfolio)
    summary = perf.performance_summary()

    print(f"Portfolio: {portfolio.name}")
    print(f"Period: {summary['period']['start_date']} to {summary['period']['end_date']}")
    print(f"Total Return: {summary['returns']['total_return']:.2%}")
    print(f"Sharpe Ratio: {summary['risk_metrics']['sharpe_ratio']:.2f}")

Portfolio Optimization
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from portfolio_manager.analytics.optimization import PortfolioOptimizer

    optimizer = PortfolioOptimizer(assets)
    
    # Maximize Sharpe ratio
    optimal = optimizer.mean_variance_optimization()
    print("Optimal weights:", optimal['weights'])
    
    # Risk parity
    risk_parity = optimizer.risk_parity_optimization()
    print("Risk parity weights:", risk_parity['weights'])

Next Steps
----------

* Explore the :doc:`tutorials/index` for in-depth guides
* Check out the :doc:`api` reference for detailed documentation
* Look at :doc:`examples` for more complex use cases
* Read about :doc:`contributing` if you want to contribute
