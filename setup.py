#!/usr/bin/env python3
"""
Portfolio Manager Setup Script

This script helps set up the development environment for the portfolio-manager package.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Error: {e.stderr}")
        return False


def check_uv_installed():
    """Check if UV is installed."""
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_uv():
    """Install UV package manager."""
    print("📦 UV not found. Installing UV...")
    
    if sys.platform.startswith('win'):
        # Windows installation
        command = 'powershell -c "irm https://astral.sh/uv/install.ps1 | iex"'
    else:
        # Unix-like systems
        command = 'curl -LsSf https://astral.sh/uv/install.sh | sh'
    
    return run_command(command, "Installing UV")


def main():
    """Main setup function."""
    print("🚀 Portfolio Manager Development Setup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Error: pyproject.toml not found. Please run this script from the project root.")
        sys.exit(1)
    
    # Check UV installation
    if not check_uv_installed():
        if not install_uv():
            print("❌ Failed to install UV. Please install manually from https://github.com/astral-sh/uv")
            sys.exit(1)
        
        # Add UV to PATH for current session
        if sys.platform.startswith('win'):
            uv_path = os.path.expanduser("~/.cargo/bin")
        else:
            uv_path = os.path.expanduser("~/.local/bin")
        
        if uv_path not in os.environ["PATH"]:
            os.environ["PATH"] = f"{uv_path}{os.pathsep}{os.environ['PATH']}"
    
    print("✅ UV is available")
    
    # Install dependencies
    commands = [
        ("uv sync --all-extras", "Installing all dependencies"),
        ("uv run pre-commit install", "Setting up pre-commit hooks"),
    ]
    
    success = True
    for command, description in commands:
        if not run_command(command, description):
            success = False
    
    if success:
        print("\n🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Run tests: uv run pytest")
        print("2. Run example: uv run python examples/basic_portfolio_example.py")
        print("3. Start developing!")
    else:
        print("\n⚠️  Setup completed with some errors. Please check the output above.")
    
    print("\n📚 Documentation:")
    print("- README.md for usage instructions")
    print("- docs/ folder for detailed documentation")
    print("- examples/ folder for example scripts")


if __name__ == "__main__":
    main()
