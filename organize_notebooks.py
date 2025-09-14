"""
Notebook Organization Script

This script organizes the EDHEC Risk Kit notebooks into a proper structure
and updates them to use the new portfolio-manager package.
"""

import os
import shutil
from pathlib import Path

def organize_notebooks():
    """Organize notebooks into proper documentation structure."""
    
    project_root = Path(".")
    docs_dir = project_root / "docs"
    tutorials_dir = docs_dir / "tutorials"
    examples_dir = docs_dir / "notebooks"
    
    # Create directories if they don't exist
    tutorials_dir.mkdir(parents=True, exist_ok=True)
    examples_dir.mkdir(parents=True, exist_ok=True)
    
    # Mapping of notebooks to categories
    notebook_categories = {
        # Basic concepts
        "lab_101.ipynb": ("tutorials", "01_basic_returns.ipynb"),
        "lab_102.ipynb": ("tutorials", "02_portfolio_returns.ipynb"), 
        "lab_103.ipynb": ("tutorials", "03_risk_measures.ipynb"),
        "lab_104.ipynb": ("tutorials", "04_risk_adjusted_returns.ipynb"),
        "lab_105.ipynb": ("tutorials", "05_historical_analysis.ipynb"),
        "lab_106.ipynb": ("tutorials", "06_diversification.ipynb"),
        "lab_107.ipynb": ("tutorials", "07_efficient_frontier.ipynb"),
        "lab_108.ipynb": ("tutorials", "08_portfolio_optimization.ipynb"),
        "lab_109.ipynb": ("tutorials", "09_factor_models.ipynb"),
        "lab_110.ipynb": ("tutorials", "10_performance_evaluation.ipynb"),
        "lab_111.ipynb": ("tutorials", "11_style_analysis.ipynb"),
        
        # Advanced topics  
        "lab_118.ipynb": ("notebooks", "advanced_cppi_implementation.ipynb"),
        "lab_119.ipynb": ("notebooks", "portfolio_insurance_cppi.ipynb"),
        "lab_121.ipynb": ("notebooks", "liability_driven_investing.ipynb"),
        "lab_122.ipynb": ("notebooks", "funding_ratio_analysis.ipynb"),
        "lab_123.ipynb": ("notebooks", "hedging_strategies.ipynb"),
        "lab_124.ipynb": ("notebooks", "dynamic_hedging.ipynb"),
        "lab_125.ipynb": ("notebooks", "liability_matching.ipynb"),
        "lab_126.ipynb": ("notebooks", "goal_based_investing.ipynb"),
        "lab_127.ipynb": ("notebooks", "glide_path_strategies.ipynb"),
        "lab_128.ipynb": ("notebooks", "monte_carlo_simulation.ipynb"),
        "lab_129.ipynb": ("notebooks", "dynamic_risk_budgeting.ipynb"),
        
        # Quizzes -> examples
        "Quiz1.ipynb": ("notebooks", "quiz_basic_concepts.ipynb"),
        "Quiz2.ipynb": ("notebooks", "quiz_portfolio_theory.ipynb"), 
        "Quizz3.ipynb": ("notebooks", "quiz_advanced_topics.ipynb"),
    }
    
    print("📚 Organizing EDHEC Risk Kit Notebooks")
    print("=" * 50)
    
    # Move and rename notebooks
    for old_name, (category, new_name) in notebook_categories.items():
        old_path = project_root / old_name
        
        if old_path.exists():
            if category == "tutorials":
                new_path = tutorials_dir / new_name
            else:
                new_path = examples_dir / new_name
            
            # Copy the notebook
            shutil.copy2(old_path, new_path)
            print(f"✅ {old_name} -> {category}/{new_name}")
            
            # Optionally remove original (commented out for safety)
            # old_path.unlink()
        else:
            print(f"⚠️  {old_name} not found")
    
    # Handle other notebooks
    other_notebooks = ["sympy.ipynb", "Untitled.ipynb", "Untitled1.ipynb", "Untitled2.ipynb"]
    archive_dir = docs_dir / "archive"
    archive_dir.mkdir(exist_ok=True)
    
    for notebook in other_notebooks:
        old_path = project_root / notebook
        if old_path.exists():
            new_path = archive_dir / notebook
            shutil.copy2(old_path, new_path)
            print(f"📦 {notebook} -> archive/")
    
    print(f"\n✨ Organization complete!")
    print(f"📁 Tutorials: {len([f for f in tutorials_dir.glob('*.ipynb')])}")
    print(f"📁 Examples: {len([f for f in examples_dir.glob('*.ipynb')])}")
    print(f"📁 Archive: {len([f for f in archive_dir.glob('*.ipynb')])}")

def create_notebook_index():
    """Create an index of all notebooks."""
    
    index_content = """# Portfolio Manager - Notebooks and Tutorials

This directory contains educational notebooks and examples for the Portfolio Manager package.

## 📚 Tutorials (docs/tutorials/)

**Basic Portfolio Theory Concepts:**

1. **Basic Returns** (`01_basic_returns.ipynb`) - Computing and analyzing returns
2. **Portfolio Returns** (`02_portfolio_returns.ipynb`) - Portfolio-level return calculations  
3. **Risk Measures** (`03_risk_measures.ipynb`) - Volatility, VaR, and risk metrics
4. **Risk-Adjusted Returns** (`04_risk_adjusted_returns.ipynb`) - Sharpe ratio and performance
5. **Historical Analysis** (`05_historical_analysis.ipynb`) - Analyzing historical data
6. **Diversification** (`06_diversification.ipynb`) - Portfolio diversification benefits
7. **Efficient Frontier** (`07_efficient_frontier.ipynb`) - Modern portfolio theory
8. **Portfolio Optimization** (`08_portfolio_optimization.ipynb`) - Optimization techniques
9. **Factor Models** (`09_factor_models.ipynb`) - Factor-based analysis
10. **Performance Evaluation** (`10_performance_evaluation.ipynb`) - Performance measurement
11. **Style Analysis** (`11_style_analysis.ipynb`) - Investment style analysis

## 🚀 Advanced Examples (docs/notebooks/)

**Portfolio Insurance & Dynamic Strategies:**
- **Portfolio Insurance (CPPI)** - Constant Proportion Portfolio Insurance
- **Dynamic Risk Budgeting** - Monte Carlo simulation techniques
- **Liability-Driven Investing** - LDI strategies and implementation

**Goal-Based & Lifecycle Investing:**  
- **Goal-Based Investing** - Target-date strategies
- **Glide Path Strategies** - Age-based allocation techniques
- **Monte Carlo Simulation** - Stochastic modeling

**Risk Management:**
- **Hedging Strategies** - Risk mitigation techniques  
- **Dynamic Hedging** - Adaptive hedging approaches
- **Liability Matching** - Duration and immunization

## 🧪 Practice & Assessment
- **Quiz Notebooks** - Self-assessment exercises
- **Interactive Examples** - Hands-on practice problems

## 🔧 Using the Notebooks

### Setup
```bash
# Install package in development mode
uv sync --all-extras

# Start Jupyter
uv run jupyter lab
```

### Package Integration
All notebooks have been updated to use the new package structure:

```python
# New imports (replace old edhec_risk_kit imports)
from portfolio_manager import Portfolio, YFinanceProvider
from portfolio_manager.analytics import PerformanceAnalytics, RiskAnalytics
from portfolio_manager.legacy.risk_functions import get_hfi_returns, skewness
```

### Data Requirements
Some notebooks require the original EDHEC data files in the `data/` directory:
- `edhec-hedgefundindices.csv`
- `Portfolios_Formed_on_ME_monthly_EW.csv` 
- `ind30_m_*.csv` files

## 📖 Learning Path

**Recommended sequence for beginners:**
1. Start with tutorials 01-05 (basic concepts)
2. Progress through 06-08 (portfolio theory) 
3. Explore 09-11 (advanced analysis)
4. Try advanced examples based on interest

**For experienced practitioners:**
- Jump to advanced examples
- Use tutorials as reference material
- Focus on implementation details

## 🤝 Contributing

When adding new notebooks:
- Place tutorials in `docs/tutorials/`
- Place examples in `docs/notebooks/`
- Update this index
- Ensure compatibility with package structure
- Add proper documentation and markdown explanations

## 🎓 Educational Value

These notebooks are based on the **EDHEC Risk Institute** curriculum and provide:
- Theoretical foundations
- Practical implementations  
- Real-world examples
- Interactive learning experiences

Perfect for students, practitioners, and researchers in quantitative finance!
"""
    
    docs_dir = Path("docs")
    index_path = docs_dir / "NOTEBOOKS_INDEX.md"
    
    with open(index_path, 'w') as f:
        f.write(index_content)
    
    print(f"📝 Created notebook index: {index_path}")

if __name__ == "__main__":
    organize_notebooks()
    create_notebook_index()
