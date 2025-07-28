#!/usr/bin/env python3
"""
Comprehensive test runner for the Review Platform
Runs frontend, backend, and GPU processing tests
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path


class TestRunner:
    """Test runner for all platform components."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.results = {
            'frontend': {'passed': 0, 'failed': 0, 'errors': []},
            'backend': {'passed': 0, 'failed': 0, 'errors': []},
            'gpu': {'passed': 0, 'failed': 0, 'errors': []}
        }
    
    def run_command(self, command, cwd=None, timeout=300):
        """Run a command and return the result."""
        try:
            print(f"Running: {' '.join(command)}")
            if cwd:
                print(f"Working directory: {cwd}")
            
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return result
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(
                command, 1, "", f"Command timed out after {timeout} seconds"
            )
        except Exception as e:
            return subprocess.CompletedProcess(
                command, 1, "", str(e)
            )
    
    def run_frontend_tests(self):
        """Run frontend tests."""
        print("\n" + "="*50)
        print("🎨 Running Frontend Tests")
        print("="*50)
        
        frontend_dir = self.project_root / "frontend"
        
        # Check if node_modules exists
        if not (frontend_dir / "node_modules").exists():
            print("Installing frontend dependencies...")
            npm_install = self.run_command(["npm", "install"], cwd=frontend_dir)
            if npm_install.returncode != 0:
                self.results['frontend']['errors'].append("Failed to install dependencies")
                print(f"❌ Failed to install dependencies: {npm_install.stderr}")
                return False
        
        # Run tests
        test_command = ["npm", "test", "--", "--watchAll=false", "--coverage"]
        result = self.run_command(test_command, cwd=frontend_dir)
        
        if result.returncode == 0:
            print("✅ Frontend tests passed")
            self.results['frontend']['passed'] = self.extract_test_count(result.stdout, "frontend")
            return True
        else:
            print("❌ Frontend tests failed")
            self.results['frontend']['failed'] = self.extract_test_count(result.stdout, "frontend")
            self.results['frontend']['errors'].append(result.stderr)
            print(f"Error: {result.stderr}")
            return False
    
    def run_backend_tests(self):
        """Run backend tests."""
        print("\n" + "="*50)
        print("🔧 Running Backend Tests")
        print("="*50)
        
        backend_dir = self.project_root / "backend"
        
        # Check if virtual environment exists and create if needed
        venv_dir = backend_dir / "venv"
        if not venv_dir.exists():
            print("Creating virtual environment...")
            create_venv = self.run_command([sys.executable, "-m", "venv", "venv"], cwd=backend_dir)
            if create_venv.returncode != 0:
                self.results['backend']['errors'].append("Failed to create virtual environment")
                print(f"❌ Failed to create virtual environment: {create_venv.stderr}")
                return False
        
        # Install dependencies
        pip_path = venv_dir / "bin" / "pip" if os.name != "nt" else venv_dir / "Scripts" / "pip.exe"
        if not pip_path.exists():
            pip_path = venv_dir / "bin" / "pip3" if os.name != "nt" else venv_dir / "Scripts" / "pip3.exe"
        
        install_cmd = [str(pip_path), "install", "-r", "requirements.txt", "-r", "tests/requirements.txt"]
        install_result = self.run_command(install_cmd, cwd=backend_dir)
        
        if install_result.returncode != 0:
            print("⚠️  Warning: Failed to install some backend dependencies")
            print(f"Install output: {install_result.stderr}")
        
        # Run tests
        python_path = venv_dir / "bin" / "python" if os.name != "nt" else venv_dir / "Scripts" / "python.exe"
        test_command = [str(python_path), "-m", "pytest", "tests/", "-v", "--cov=app", "--cov-report=term-missing"]
        result = self.run_command(test_command, cwd=backend_dir)
        
        if result.returncode == 0:
            print("✅ Backend tests passed")
            self.results['backend']['passed'] = self.extract_test_count(result.stdout, "backend")
            return True
        else:
            print("❌ Backend tests failed")
            self.results['backend']['failed'] = self.extract_test_count(result.stdout, "backend")
            self.results['backend']['errors'].append(result.stderr)
            print(f"Error: {result.stderr}")
            return False
    
    def run_gpu_tests(self):
        """Run GPU processing tests."""
        print("\n" + "="*50)
        print("🖥️  Running GPU Processing Tests")
        print("="*50)
        
        gpu_dir = self.project_root / "gpu_processing"
        
        # Install test dependencies
        install_cmd = [sys.executable, "-m", "pip", "install", "-r", "tests/requirements.txt", "--break-system-packages"]
        install_result = self.run_command(install_cmd, cwd=gpu_dir)
        
        if install_result.returncode != 0:
            print("⚠️  Warning: Failed to install some GPU test dependencies")
            print(f"Install output: {install_result.stderr}")
        
        # Run tests
        test_command = [sys.executable, "-m", "pytest", "tests/", "-v", "--cov=.", "--cov-report=term-missing"]
        result = self.run_command(test_command, cwd=gpu_dir)
        
        if result.returncode == 0:
            print("✅ GPU processing tests passed")
            self.results['gpu']['passed'] = self.extract_test_count(result.stdout, "gpu")
            return True
        else:
            print("❌ GPU processing tests failed")
            self.results['gpu']['failed'] = self.extract_test_count(result.stdout, "gpu")
            self.results['gpu']['errors'].append(result.stderr)
            print(f"Error: {result.stderr}")
            return False
    
    def extract_test_count(self, output, component):
        """Extract test count from test output."""
        # This is a simplified extraction - in practice you'd parse the specific test runner output
        if "passed" in output.lower():
            # Try to extract number from pytest output
            import re
            match = re.search(r'(\d+) passed', output)
            if match:
                return int(match.group(1))
        return 1 if "passed" in output.lower() else 0
    
    def run_all_tests(self):
        """Run all test suites."""
        print("🚀 Starting comprehensive test suite")
        print(f"Project root: {self.project_root}")
        
        start_time = time.time()
        
        # Run each test suite
        frontend_result = self.run_frontend_tests()
        backend_result = self.run_backend_tests()
        gpu_result = self.run_gpu_tests()
        
        end_time = time.time()
        
        # Print summary
        self.print_summary(end_time - start_time)
        
        # Return overall success
        return all([frontend_result, backend_result, gpu_result])
    
    def print_summary(self, duration):
        """Print test summary."""
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        total_passed = sum(r['passed'] for r in self.results.values())
        total_failed = sum(r['failed'] for r in self.results.values())
        total_errors = sum(len(r['errors']) for r in self.results.values())
        
        print(f"⏱️  Total duration: {duration:.2f} seconds")
        print(f"✅ Total tests passed: {total_passed}")
        print(f"❌ Total tests failed: {total_failed}")
        print(f"🚨 Total errors: {total_errors}")
        
        print("\nComponent breakdown:")
        for component, results in self.results.items():
            status = "✅" if results['failed'] == 0 and len(results['errors']) == 0 else "❌"
            print(f"  {status} {component.capitalize()}: {results['passed']} passed, {results['failed']} failed")
            
            if results['errors']:
                print(f"    🚨 Errors: {len(results['errors'])}")
        
        if total_failed > 0 or total_errors > 0:
            print("\n🔍 Error details:")
            for component, results in self.results.items():
                if results['errors']:
                    print(f"\n{component.capitalize()} errors:")
                    for i, error in enumerate(results['errors'], 1):
                        print(f"  {i}. {error[:200]}...")
        
        # Overall status
        if total_failed == 0 and total_errors == 0:
            print("\n🎉 ALL TESTS PASSED!")
        else:
            print(f"\n💥 {total_failed + total_errors} ISSUES FOUND")
    
    def run_specific_suite(self, suite):
        """Run a specific test suite."""
        if suite == "frontend":
            return self.run_frontend_tests()
        elif suite == "backend":
            return self.run_backend_tests()
        elif suite == "gpu":
            return self.run_gpu_tests()
        else:
            print(f"❌ Unknown test suite: {suite}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run Review Platform tests")
    parser.add_argument(
        "--suite", 
        choices=["frontend", "backend", "gpu", "all"], 
        default="all",
        help="Test suite to run"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if args.suite == "all":
        success = runner.run_all_tests()
    else:
        success = runner.run_specific_suite(args.suite)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()