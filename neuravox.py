#!/usr/bin/env python3
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
# First try to load from ~/.neuravox/.env (production)
neuravox_env = Path.home() / ".neuravox" / ".env"
if neuravox_env.exists():
    load_dotenv(neuravox_env)
else:
    # Fall back to local .env for development
    load_dotenv()

# Add current directory to Python path for local development
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the CLI
from neuravox.cli.main import app

if __name__ == "__main__":
    app()