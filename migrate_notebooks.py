#!/usr/bin/env python3
"""
Notebook Migration Script

This script helps migrate existing EDHEC Risk Kit notebooks to use the new
portfolio-manager package structure.
"""

import re
import json
from pathlib import Path
from typing import Dict, List

def update_notebook_imports(notebook_path: Path) -> bool:
    """
    Update imports in a Jupyter notebook to use the new package structure.
    
    Args:
        notebook_path: Path to the notebook file
        
    Returns:
        True if notebook was updated, False otherwise
    """
    try:
        # Read notebook
        with open(notebook_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)
        
        updated = False
        
        # Process each cell
        for cell in notebook.get('cells', []):
            if cell.get('cell_type') == 'code':
                source = cell.get('source', [])
                if isinstance(source, str):
                    source = [source]
                
                new_source = []
                for line in source:
                    # Update imports
                    line = update_import_line(line)
                    new_source.append(line)
                
                # Check if anything changed
                if new_source != source:
                    cell['source'] = new_source
                    updated = True
        
        # Write back if updated
        if updated:
            with open(notebook_path, 'w', encoding='utf-8') as f:
                json.dump(notebook, f, indent=2, ensure_ascii=False)
            return True
            
    except Exception as e:
        print(f"Error processing {notebook_path}: {e}")
        return False
    
    return False

def update_import_line(line: str) -> str:
    """Update a single line to use new imports."""
    
    # Common replacements
    replacements = {
        # Old edhec_risk_kit imports
        r'import edhec_risk_kit as erk': 'from portfolio_manager.legacy import risk_functions as erk',
        r'import edhec_risk_kit_\d+ as erk': 'from portfolio_manager.legacy import risk_functions as erk',
        r'%run risk\.py': '# Replaced by package imports\nfrom portfolio_manager.legacy import risk_functions as erk',
        
        # Add new package imports at the top
        r'^import pandas as pd$': '''import pandas as pd
# Portfolio Manager imports
from portfolio_manager import Portfolio, YFinanceProvider
from portfolio_manager.analytics import PerformanceAnalytics, RiskAnalytics
from portfolio_manager.legacy import risk_functions as erk''',
    }
    
    for pattern, replacement in replacements.items():
        line = re.sub(pattern, replacement, line)
    
    return line

def create_notebook_template() -> str:
    """Create a template for new notebooks."""
    return '''# Portfolio Manager Notebook Template

## Setup

Add this cell at the beginning of your notebooks:

```python
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Portfolio Manager imports
from portfolio_manager import Portfolio, YFinanceProvider
from portfolio_manager.analytics import PerformanceAnalytics, RiskAnalytics, PortfolioOptimizer
from portfolio_manager.legacy import risk_functions as erk

# Configuration
plt.style.use('seaborn-v0_8')
pd.set_option('display.max_columns', None)
np.random.seed(42)

print("Portfolio Manager environment ready!")
```

## Data Loading

```python
# Load EDHEC data (legacy functions)
hfi_returns = erk.get_hfi_returns()
ind_returns = erk.get_ind_returns()

# Load market data (new providers)
provider = YFinanceProvider()
assets = provider.get_multiple_assets(['SPY', 'BND', 'VTI'], 
                                    start_date=pd.Timestamp('2020-01-01'))
```

## Portfolio Creation

```python
# Create portfolio
portfolio = Portfolio(name="Sample Portfolio")

# Add assets
portfolio.add_asset('SPY', assets[0], 0.6)
portfolio.add_asset('BND', assets[1], 0.4)

# Analyze performance
perf = PerformanceAnalytics(portfolio)
risk = RiskAnalytics(portfolio)

print(f"Sharpe Ratio: {perf.sharpe_ratio():.2f}")
print(f"Volatility: {perf.volatility():.2%}")
```

## Migration Notes

- Replace `import edhec_risk_kit as erk` with new imports
- Use `portfolio_manager.legacy.risk_functions` for original functions
- New functionality available via Portfolio and Analytics classes
- All original EDHEC data loading functions preserved
'''

def main():
    """Main migration function."""
    print("Portfolio Manager Notebook Migration Tool")
    print("=" * 50)
    
    # Create template file
    template_path = Path("docs/NOTEBOOK_TEMPLATE.md")
    template_path.parent.mkdir(exist_ok=True)
    
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(create_notebook_template())
    
    print(f"✅ Created notebook template: {template_path}")
    
    # Find notebooks to migrate
    notebook_files = list(Path(".").glob("*.ipynb"))
    
    if not notebook_files:
        print("ℹ️  No notebooks found in current directory")
        return
    
    print(f"\nFound {len(notebook_files)} notebooks to potentially migrate:")
    for nb in notebook_files:
        print(f"  📔 {nb.name}")
    
    print("\n🔧 To migrate notebooks:")
    print("1. Move notebooks to appropriate directories (see NOTEBOOK_ORGANIZATION_GUIDE.md)")
    print("2. Run this script in each directory")
    print("3. Test notebooks to ensure imports work")
    print("4. Update any remaining manual imports")
    
    # Optional: Ask for confirmation to migrate
    # migrate = input("\nMigrate imports in these notebooks? (y/N): ").lower().strip()
    # if migrate == 'y':
    #     for notebook_path in notebook_files:
    #         if update_notebook_imports(notebook_path):
    #             print(f"✅ Updated {notebook_path}")
    #         else:
    #             print(f"⚠️  No changes needed for {notebook_path}")

if __name__ == "__main__":
    main()
