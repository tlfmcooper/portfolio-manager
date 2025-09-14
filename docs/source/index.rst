Portfolio Manager Documentation
=============================

.. image:: https://img.shields.io/badge/python-3.9+-blue.svg
   :target: https://www.python.org/downloads/
   :alt: Python 3.9+

.. image:: https://img.shields.io/badge/License-MIT-yellow.svg
   :target: https://opensource.org/licenses/MIT
   :alt: License: MIT

A comprehensive Python package for portfolio management and analysis, built on modern portfolio theory and EDHEC Risk Kit methodology.

Features
--------

* **Portfolio Construction**: Build and manage investment portfolios with multiple assets
* **Risk Analytics**: Comprehensive risk analysis including VaR, correlation analysis, and stress testing  
* **Performance Analytics**: Calculate returns, Sharpe ratios, drawdowns, and other performance metrics
* **Portfolio Optimization**: Modern portfolio theory optimization including mean-variance, risk parity, and Black-Litterman
* **Data Integration**: Seamless integration with Yahoo Finance and other data providers
* **Legacy Support**: Backward compatibility with EDHEC Risk Kit functions

Quick Start
-----------

Installation
~~~~~~~~~~~~

Using UV (recommended)::

    uv add portfolio-manager

Using pip::

    pip install portfolio-manager

Basic Usage
~~~~~~~~~~~

.. code-block:: python

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

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   getting_started
   tutorials/index
   api
   examples
   contributing

.. toctree::
   :maxdepth: 1
   :caption: API Reference:

   api/core
   api/analytics
   api/data
   api/legacy

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
