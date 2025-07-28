#!/usr/bin/env python3
"""
Test runner script for the backend test suite
"""

import subprocess
import sys
import os
from pathlib import Path

def run_tests():
    """Run the test suite with proper configuration"""
    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    # Common pytest arguments
    pytest_args = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--color=yes"
    ]
    
    # Check if coverage is requested
    if "--coverage" in sys.argv:
        pytest_args.extend([
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ])
    
    # Check if specific test type is requested
    if "--unit" in sys.argv:
        pytest_args.append("tests/unit/")
    elif "--integration" in sys.argv:
        pytest_args.append("tests/integration/")
    
    # Run pytest
    try:
        result = subprocess.run(pytest_args, check=True)
        print("\n✅ All tests passed!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Tests failed with exit code {e.returncode}")
        return e.returncode
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Error running tests: {e}")
        return 1

def main():
    """Main entry point"""
    if "--help" in sys.argv:
        print("""
Backend Test Runner

Usage:
    python run_tests.py [options]

Options:
    --unit          Run only unit tests
    --integration   Run only integration tests
    --coverage      Run tests with coverage reporting
    --help          Show this help message

Examples:
    python run_tests.py                    # Run all tests
    python run_tests.py --unit             # Run only unit tests
    python run_tests.py --coverage         # Run with coverage
    python run_tests.py --unit --coverage  # Unit tests with coverage
        """)
        return 0
    
    return run_tests()

if __name__ == "__main__":
    sys.exit(main())