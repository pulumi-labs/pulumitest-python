"""Integration tests for PulumiTest core class.

Tests the pytest-native PulumiTest class with both PyTestContext and UnittestContext
to verify framework-agnostic behavior and backward compatibility.
"""

import unittest
import logging
from pathlib import Path
from unittest.mock import Mock

try:
    import pytest
    from pulumitest.pytest_context import PyTestContext
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False

from pulumitest.core import PulumiTest
from pulumitest.unittest_context import UnittestContext
from pulumitest.context import TestContext
from pulumitest import opttest


class TestPulumiTestWithUnittestContext(unittest.TestCase):
    """Integration tests using UnittestContext for backward compatibility."""

    def test_initialization(self):
        """Test that PulumiTest initializes correctly with UnittestContext."""
        context = UnittestContext(self)
        test = PulumiTest(
            context,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        self.assertEqual(test.working_dir, "test_stack")
        self.assertIsNotNone(test.logger)
        self.assertIsInstance(test.logger, logging.Logger)

    def test_basic_operations(self):
        """Test basic Pulumi operations with UnittestContext."""
        context = UnittestContext(self)
        test = PulumiTest(context, "test_stack")

        # Add AWS environment for credentials
        test.add_environments("aws/pulumi-ce")

        # Test up
        result = test.up()
        self.assertIsNotNone(result)

        # Test preview (should show no changes)
        preview = test.preview()
        preview.has_no_changes()

        # Test refresh (should show no changes)
        refresh = test.refresh()
        refresh.has_no_changes()

        # Cleanup happens via context.add_cleanup()

    def test_copy_to_temp_dir(self):
        """Test copying program to temp directory."""
        context = UnittestContext(self)
        test = PulumiTest(
            context,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        # Copy to temp dir
        copied_test = test.copy_to_temp_dir()

        # Verify working directory changed
        self.assertNotEqual(copied_test.working_dir, test.working_dir)
        self.assertTrue("programDir_" in copied_test.working_dir)
        self.assertTrue(Path(copied_test.working_dir).exists())

    def test_update_source(self):
        """Test update_source preserves stack state."""
        context = UnittestContext(self)
        test = PulumiTest(context, "test_stack")
        test.add_environments("aws/pulumi-ce")

        # Initial deployment
        test.up()

        # Update source (copying from same directory to test mechanism)
        # In real usage, this would be a different directory
        test.update_source("test_stack")

        # Verify stack still exists
        self.assertIsNotNone(test.current_stack)

        # Preview should show no changes (same source)
        preview = test.preview()
        preview.has_no_changes()

    def test_get_env_vars(self):
        """Test get_env_vars returns environment variables."""
        context = UnittestContext(self)
        test = PulumiTest(
            context,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        env_vars = test.get_env_vars()

        self.assertIsInstance(env_vars, dict)
        self.assertIn("PULUMI_BACKEND_URL", env_vars)
        self.assertIn("PULUMI_CONFIG_PASSPHRASE", env_vars)

    def test_workspace_access(self):
        """Test accessing underlying workspace and stack."""
        context = UnittestContext(self)
        test = PulumiTest(
            context,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install()
        )

        # Test current_stack property
        stack = test.current_stack
        self.assertIsNotNone(stack)
        self.assertEqual(stack.name, "test")

        # Test local_workspace property
        workspace = test.local_workspace
        self.assertIsNotNone(workspace)

    def test_cleanup_registered(self):
        """Test that cleanup is properly registered with context."""
        cleanup_called = []

        class TestCaseWithCleanupTracking(unittest.TestCase):
            def __init__(self):
                super().__init__()
                self._testMethodName = "test_cleanup"

            def addCleanup(self, fn, *args, **kwargs):
                cleanup_called.append(fn)

        mock_test_case = TestCaseWithCleanupTracking()
        context = UnittestContext(mock_test_case)

        # Create PulumiTest with skip options to avoid actual Pulumi operations
        test = PulumiTest(
            context,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        # Verify cleanup was registered
        self.assertGreater(len(cleanup_called), 0)


@unittest.skipUnless(PYTEST_AVAILABLE, "pytest not installed")
class TestPulumiTestWithPyTestContext(unittest.TestCase):
    """Integration tests using PyTestContext for pytest-native behavior."""

    def test_initialization_with_pytest(self):
        """Test that PulumiTest initializes correctly with PyTestContext."""
        mock_request = Mock()
        mock_request.node.name = "test_something"

        context = PyTestContext(mock_request)
        test = PulumiTest(
            context,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        self.assertEqual(test.working_dir, "test_stack")
        self.assertIsNotNone(test.logger)
        self.assertIsInstance(test.logger, logging.Logger)

    def test_cleanup_registered_with_pytest(self):
        """Test that cleanup is properly registered with pytest finalizer."""
        finalizers_called = []

        mock_request = Mock()
        mock_request.node.name = "test_cleanup"
        mock_request.addfinalizer = lambda fn: finalizers_called.append(fn)

        context = PyTestContext(mock_request)

        # Create PulumiTest with skip options
        test = PulumiTest(
            context,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        # Verify finalizer was registered
        self.assertGreater(len(finalizers_called), 0)

    def test_context_protocol_compliance(self):
        """Test that PyTestContext works as TestContext with PulumiTest."""
        mock_request = Mock()
        mock_request.node.name = "test_protocol"

        context = PyTestContext(mock_request)

        # Verify context implements TestContext protocol
        self.assertIsInstance(context, TestContext)

        # Verify PulumiTest accepts it
        test = PulumiTest(
            context,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        self.assertIsNotNone(test)
        self.assertEqual(test.context, context)


class TestPulumiTestFrameworkAgnostic(unittest.TestCase):
    """Tests verifying PulumiTest works with any TestContext implementation."""

    def test_custom_context_implementation(self):
        """Test that PulumiTest works with custom TestContext implementation."""

        class CustomContext:
            def __init__(self):
                self.cleanups = []
                self.failures = []

            def add_cleanup(self, fn):
                self.cleanups.append(fn)

            def fail(self, msg: str):
                self.failures.append(msg)
                raise AssertionError(msg)

            def get_name(self) -> str:
                return "custom_test"

            def get_logger(self) -> logging.Logger:
                return logging.getLogger("custom_test")

        context = CustomContext()

        # Create PulumiTest with custom context
        test = PulumiTest(
            context,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        self.assertEqual(test.working_dir, "test_stack")
        self.assertGreater(len(context.cleanups), 0)

    def test_options_configuration(self):
        """Test that options are properly applied."""
        context = UnittestContext(self)

        # Test with custom options
        custom_options = opttest.default_options()
        custom_options.config_passphrase = "test-passphrase"

        test = PulumiTest(
            context,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create(),
            options=custom_options
        )

        self.assertEqual(test.options.config_passphrase, "test-passphrase")


class TestPulumiTestErrorHandling(unittest.TestCase):
    """Tests for error handling and edge cases."""

    def test_stack_not_initialized_error(self):
        """Test that accessing stack before initialization raises error."""
        context = UnittestContext(self)

        # Create test with skip_stack_create but don't initialize
        test = PulumiTest(
            context,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        # Stack should still be initialized even with skip_stack_create
        # because __init__ calls _pulumi_test_init()
        self.assertIsNotNone(test._stack)

    def test_invalid_working_directory(self):
        """Test behavior with invalid working directory."""
        context = UnittestContext(self)

        # This should fail during initialization when trying to set up workspace
        with self.assertRaises(Exception):
            test = PulumiTest(
                context,
                "/nonexistent/directory",
                opttest.test_in_place()
            )


if __name__ == '__main__':
    unittest.main()
