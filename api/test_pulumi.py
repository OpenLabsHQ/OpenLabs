#!/usr/bin/env python3
"""
Test runner script for Pulumi migration.

This script demonstrates how to run the new Pulumi tests after installing dependencies.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} - SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"   Error: {e.stderr}")
        return False


def main():
    """Main test runner function."""
    print("🚀 Pulumi Migration Test Runner")
    print("=" * 50)
    
    # Change to the API directory
    api_dir = Path(__file__).parent
    print(f"Working directory: {api_dir}")
    
    tests_to_run = [
        {
            "cmd": ["python", "-m", "pytest", "tests/unit/core/pulumi/ranges/test_range_factory.py", "-v"],
            "description": "Pulumi Range Factory Tests"
        },
        {
            "cmd": ["python", "-m", "pytest", "tests/unit/core/pulumi/ranges/test_base_range.py", "-v"],
            "description": "Pulumi Base Range Tests"
        },
        {
            "cmd": ["python", "-m", "pytest", "tests/unit/core/pulumi/ranges/test_aws_range.py", "-v"],
            "description": "Pulumi AWS Range Tests"
        },
        {
            "cmd": ["python", "-m", "pytest", "tests/unit/worker/test_pulumi_ranges.py", "-v"],
            "description": "Pulumi Worker Tests"
        },
        {
            "cmd": ["python", "-m", "pytest", "tests/integration/core/pulumi/test_pulumi_integration.py", "-v", "-m", "integration"],
            "description": "Pulumi Integration Tests"
        }
    ]
    
    print("\nIMPORTANT: Before running these tests, make sure to:")
    print("1. Install the new dependencies: pip install -r requirements.txt")
    print("2. Install test dependencies: pip install -r dev-requirements.txt")
    print("3. Make sure Pulumi CLI is available in PATH")
    print("")
    
    # Check if Pulumi dependencies are available
    try:
        import pulumi
        import pulumi_aws
        print("✅ Pulumi dependencies are installed")
    except ImportError as e:
        print(f"❌ Pulumi dependencies not installed: {e}")
        print("\nTo install Pulumi dependencies:")
        print("  pip install pulumi>=3.0.0 pulumi-aws>=6.0.0")
        return False
    
    print("\n📋 Running Pulumi Tests...")
    print("-" * 30)
    
    success_count = 0
    total_tests = len(tests_to_run)
    
    for test in tests_to_run:
        if run_command(test["cmd"], test["description"]):
            success_count += 1
        print()
    
    print("📊 Test Results Summary:")
    print(f"   ✅ Passed: {success_count}/{total_tests}")
    print(f"   ❌ Failed: {total_tests - success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("\n🎉 All Pulumi tests passed! Migration is working correctly.")
        return True
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)