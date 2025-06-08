#!/usr/bin/env python3
"""
Test runner for neuravox
"""
import subprocess
import sys
from pathlib import Path
import argparse


def run_tests(test_type=None, verbose=False, generate_fixtures=False):
    """Run tests with various options"""
    
    # Generate test fixtures if requested
    if generate_fixtures:
        print("Generating test audio files...")
        fixtures_dir = Path(__file__).parent / "tests" / "fixtures"
        subprocess.run([
            sys.executable, 
            "tests/generate_test_audio.py", 
            str(fixtures_dir)
        ])
        print()
    
    # Build pytest command
    cmd = [sys.executable, "-m", "pytest"]
    
    # Add test type filter
    if test_type == "unit":
        cmd.extend(["tests/unit", "-m", "unit"])
    elif test_type == "integration":
        cmd.extend(["tests/integration", "-m", "integration"])
    
    # Add verbosity
    if verbose:
        cmd.append("-vv")
    
    # Add coverage if available
    try:
        import pytest_cov
        cmd.extend(["--cov=modules", "--cov=core", "--cov=cli", "--cov-report=term-missing"])
    except ImportError:
        pass
    
    # Run tests
    print(f"Running command: {' '.join(cmd)}")
    print("-" * 50)
    
    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Run tests for neuravox")
    parser.add_argument(
        "type",
        nargs="?",
        choices=["all", "unit", "integration"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "-g", "--generate-fixtures",
        action="store_true",
        help="Generate test audio fixtures before running tests"
    )
    
    args = parser.parse_args()
    
    # Determine test type
    test_type = None if args.type == "all" else args.type
    
    # Run tests
    exit_code = run_tests(
        test_type=test_type,
        verbose=args.verbose,
        generate_fixtures=args.generate_fixtures
    )
    
    # Print summary
    print("\n" + "=" * 50)
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()