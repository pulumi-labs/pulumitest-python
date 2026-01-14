"""Pytest configuration for tests.

This conftest.py makes pulumitest fixtures available to all tests
without requiring package installation.
"""

# Import pytest plugin to register fixtures
pytest_plugins = ["pulumitest.pytest_plugin"]
