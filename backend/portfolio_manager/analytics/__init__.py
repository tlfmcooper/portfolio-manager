"""
Analytics module for portfolio analysis.
"""

from .performance import PerformanceAnalytics
from .risk import RiskAnalytics  
from .optimization import PortfolioOptimizer

# Import all risk metrics functions
from .risk_metrics import (
    # Data loading functions
    get_ffme_returns, get_hfi_returns, get_ind_file, get_ind_returns, 
    get_ind_nfirms, get_ind_size, get_total_market_index_returns,
    
    # Basic statistical functions
    skewness, kurtosis, compound, annualize_rets, annualize_vol, 
    sharpe_ratio, is_normal, drawdown, semideviation, var_historic, 
    cvar_historic, var_gaussian,
    
    # Portfolio functions  
    portfolio_return, portfolio_vol, plot_ef2, minimize_vol, msr, gmv, 
    optimal_weights, plot_ef,
    
    # CPPI and dynamic strategies
    run_cppi, summary_stats,
    
    # Monte Carlo simulation
    gbm,
    
    # Fixed income functions
    discount, pv, funding_ratio, inst_to_ann, ann_to_inst, cir,
    bond_cash_flows, bond_price, macaulay_duration, match_durations, 
    bond_total_return,
    
    # Backtesting and allocation strategies
    bt_mix, fixedmix_allocator, terminal_values, terminal_stats,
    glidepath_allocator, floor_allocator, drawdown_allocator
)

__all__ = [
    "PerformanceAnalytics", "RiskAnalytics", "PortfolioOptimizer",
    
    # Data loading functions
    "get_ffme_returns", "get_hfi_returns", "get_ind_file", "get_ind_returns", 
    "get_ind_nfirms", "get_ind_size", "get_total_market_index_returns",
    
    # Basic statistical functions
    "skewness", "kurtosis", "compound", "annualize_rets", "annualize_vol", 
    "sharpe_ratio", "is_normal", "drawdown", "semideviation", "var_historic", 
    "cvar_historic", "var_gaussian",
    
    # Portfolio functions  
    "portfolio_return", "portfolio_vol", "plot_ef2", "minimize_vol", "msr", "gmv", 
    "optimal_weights", "plot_ef",
    
    # CPPI and dynamic strategies
    "run_cppi", "summary_stats",
    
    # Monte Carlo simulation
    "gbm",
    
    # Fixed income functions
    "discount", "pv", "funding_ratio", "inst_to_ann", "ann_to_inst", "cir",
    "bond_cash_flows", "bond_price", "macaulay_duration", "match_durations", 
    "bond_total_return",
    
    # Backtesting and allocation strategies
    "bt_mix", "fixedmix_allocator", "terminal_values", "terminal_stats",
    "glidepath_allocator", "floor_allocator", "drawdown_allocator"
]
