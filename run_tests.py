#!/usr/bin/env python3
"""One-command test runner for FileConverter backend tests.

Usage:
    python run_tests.py          # Run all tests with verbose output
    python run_tests.py -q       # Quiet mode
"""

import sys
import unittest

if __name__ == "__main__":
    # Discover and run all tests in the tests/ directory
    loader = unittest.TestLoader()
    suite = loader.discover("tests", pattern="test_*.py", top_level_dir=".")

    runner = unittest.TextTestRunner(verbosity=2 if "-q" not in sys.argv else 1)
    result = runner.run(suite)

    # Exit with non-zero code if any tests failed
    sys.exit(0 if result.wasSuccessful() else 1)