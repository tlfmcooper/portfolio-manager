#!/usr/bin/env python3
"""
Test the backend API to see if it returns the same data as the demo module.
"""

import requests
import json

def test_api():
    try:
        # Test the portfolio metrics endpoint
        url = "http://127.0.0.1:8000/api/v1/analysis/portfolios/1/analysis/metrics"
        print(f"Testing API endpoint: {url}")
        
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            print("\n=== API Response ===")
            print(f"Total Portfolio Value: ${data.get('total_portfolio_value', 0):,.2f}")
            print(f"Annualized Return: {data.get('portfolio_return_annualized', 0):.2%}")
            print(f"Annualized Volatility: {data.get('portfolio_volatility_annualized', 0):.2%}")
            print(f"Sharpe Ratio: {data.get('sharpe_ratio', 0):.3f}")
            print(f"Value at Risk (95%): {data.get('value_at_risk_95', 0):.2%}")
            print(f"Maximum Drawdown: {data.get('max_drawdown', 0):.2%}")
            print(f"Concentration Risk: {data.get('concentration_risk', 0):.2%}")
            
            print("\n=== Individual Performance ===")
            individual_perf = data.get('individual_performance', {})
            for symbol, perf in individual_perf.items():
                print(f"{symbol}: Return={perf.get('return', 0):.2%}, Volatility={perf.get('volatility', 0):.2%}")
            
            print(f"\n=== Full JSON Response ===")
            print(json.dumps(data, indent=2))
            
        else:
            print(f"API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error testing API: {e}")

if __name__ == "__main__":
    test_api()
