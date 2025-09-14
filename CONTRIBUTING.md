# Contributing to Portfolio Manager

Thank you for your interest in contributing to Portfolio Manager! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to a code of conduct that we expect all contributors to follow. Please be respectful and constructive in all interactions.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/portfolio-manager.git
   cd portfolio-manager
   ```
3. **Set up the development environment** (see below)

## Development Setup

### Prerequisites

- Python 3.9 or higher
- UV package manager (will be installed automatically if needed)

### Quick Setup

Run the setup script:

```bash
python setup.py
```

This will:
- Install UV if not present
- Install all dependencies
- Set up pre-commit hooks

### Manual Setup

If you prefer manual setup:

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh  # Unix/macOS
# or
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# Install dependencies
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install
```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-new-optimizer` for new features
- `fix/portfolio-weight-validation` for bug fixes
- `docs/update-readme` for documentation
- `refactor/improve-performance` for refactoring

### Development Workflow

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the code style guidelines

3. **Add tests** for new functionality

4. **Run tests** to ensure everything works:
   ```bash
   uv run pytest
   ```

5. **Run code quality checks**:
   ```bash
   uv run black src/ tests/          # Format code
   uv run isort src/ tests/          # Sort imports
   uv run flake8 src/ tests/         # Lint code
   uv run mypy src/                  # Type checking
   ```

6. **Commit your changes** with a descriptive message

7. **Push to your fork** and create a pull request

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=portfolio_manager --cov-report=html

# Run specific test file
uv run pytest tests/test_portfolio.py

# Run tests matching a pattern
uv run pytest -k "test_portfolio"
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files `test_*.py`
- Use descriptive test function names: `test_portfolio_creation_with_valid_data`
- Use fixtures for common test data (see `tests/conftest.py`)
- Aim for high test coverage on new code

### Test Categories

- **Unit tests**: Test individual functions and classes
- **Integration tests**: Test component interactions
- **End-to-end tests**: Test complete workflows

## Code Style

We use several tools to maintain code quality:

### Formatting
- **Black** for code formatting (line length: 88)
- **isort** for import sorting

### Linting
- **Flake8** for style and error checking
- **mypy** for type checking

### Type Hints
- Use type hints for all public functions and methods
- Use `Optional[Type]` for optional parameters
- Import types from `typing` module

### Documentation
- Use Google-style docstrings
- Document all public classes, functions, and methods
- Include parameter types and return types in docstrings

Example:
```python
def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """
    Calculate the Sharpe ratio for a series of returns.
    
    Args:
        returns: Series of portfolio returns
        risk_free_rate: Annual risk-free rate (default: 0.02)
        
    Returns:
        The Sharpe ratio as a float
        
    Raises:
        ValueError: If returns series is empty
    """
```

## Submitting Changes

### Pull Request Process

1. **Update documentation** if needed
2. **Add tests** for new functionality
3. **Ensure all tests pass**
4. **Update CHANGELOG.md** with your changes
5. **Create pull request** with:
   - Clear title and description
   - Reference to related issues
   - Summary of changes made

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Added/updated tests
- [ ] All tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

### Review Process

- All PRs require review from maintainers
- Address review comments promptly
- Keep PRs focused and reasonably sized
- Be open to feedback and suggestions

## Release Process

### Version Numbers

We follow [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH`
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes (backward compatible)

### Release Steps

1. Update version in `src/portfolio_manager/__init__.py`
2. Update `CHANGELOG.md`
3. Create release tag: `git tag v1.0.0`
4. Push tag: `git push origin v1.0.0`
5. GitHub Actions will automatically publish to PyPI

## Getting Help

- **Issues**: Open an issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check the docs/ folder
- **Examples**: Look at examples/ folder for usage patterns

## Recognition

Contributors will be recognized in:
- CHANGELOG.md for significant contributions
- README.md contributors section
- Release notes for major contributions

Thank you for contributing to Portfolio Manager! 🚀
