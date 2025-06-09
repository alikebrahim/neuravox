#!/usr/bin/env python3
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import and run the CLI
from neuravox.cli.main import app

if __name__ == "__main__":
    app()