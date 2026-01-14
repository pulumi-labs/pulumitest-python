"""Unit tests for TestContext implementations."""

import unittest
import logging
from typing import Callable
from unittest.mock import Mock, MagicMock

from pulumitest.context import TestContext
from pulumitest.unittest_context import UnittestContext

# Test PyTestContext only if pytest is available
try:
    import pytest
    from pulumitest.pytest_context import PyTestContext
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False


class TestUnittestContext(unittest.TestCase):
    """Tests for UnittestContext."""

    def test_add_cleanup_registers_with_testcase(self):
        """Test that add_cleanup registers cleanup with TestCase.addCleanup."""
        mock_test_case = Mock(spec=unittest.TestCase)
        mock_test_case._testMethodName = "test_something"

        context = UnittestContext(mock_test_case)
        cleanup_fn = Mock()

        context.add_cleanup(cleanup_fn)

        mock_test_case.addCleanup.assert_called_once_with(cleanup_fn)

    def test_fail_calls_testcase_fail(self):
        """Test that fail() calls TestCase.fail()."""
        mock_test_case = Mock(spec=unittest.TestCase)
        mock_test_case._testMethodName = "test_something"

        context = UnittestContext(mock_test_case)

        context.fail("Test failure message")

        mock_test_case.fail.assert_called_once_with("Test failure message")

    def test_get_name_returns_test_method_name(self):
        """Test that get_name() returns the test method name."""
        mock_test_case = Mock(spec=unittest.TestCase)
        mock_test_case._testMethodName = "test_my_function"

        context = UnittestContext(mock_test_case)

        self.assertEqual(context.get_name(), "test_my_function")

    def test_get_logger_returns_logger(self):
        """Test that get_logger() returns a logging.Logger."""
        mock_test_case = Mock(spec=unittest.TestCase)
        mock_test_case._testMethodName = "test_something"

        context = UnittestContext(mock_test_case)
        logger = context.get_logger()

        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "test_something")

    def test_protocol_compliance(self):
        """Test that UnittestContext implements TestContext protocol."""
        mock_test_case = Mock(spec=unittest.TestCase)
        mock_test_case._testMethodName = "test_something"

        context = UnittestContext(mock_test_case)

        # Check that it's recognized as TestContext
        self.assertIsInstance(context, TestContext)


@unittest.skipUnless(PYTEST_AVAILABLE, "pytest not installed")
class TestPyTestContext(unittest.TestCase):
    """Tests for PyTestContext."""

    def test_import_error_without_pytest(self):
        """Test that importing PyTestContext without pytest raises ImportError."""
        # This test is skipped when pytest is available
        # It's here as documentation of expected behavior
        pass

    def test_add_cleanup_registers_finalizer(self):
        """Test that add_cleanup registers finalizer with request."""
        mock_request = Mock()
        mock_request.node.name = "test_something"

        context = PyTestContext(mock_request)
        cleanup_fn = Mock()

        context.add_cleanup(cleanup_fn)

        mock_request.addfinalizer.assert_called_once_with(cleanup_fn)

    def test_fail_calls_pytest_fail(self):
        """Test that fail() calls pytest.fail()."""
        mock_request = Mock()
        mock_request.node.name = "test_something"

        context = PyTestContext(mock_request)

        with pytest.raises(pytest.fail.Exception):
            context.fail("Test failure message")

    def test_get_name_returns_node_name(self):
        """Test that get_name() returns the node name from request."""
        mock_request = Mock()
        mock_request.node.name = "test_my_function"

        context = PyTestContext(mock_request)

        self.assertEqual(context.get_name(), "test_my_function")

    def test_get_logger_returns_logger(self):
        """Test that get_logger() returns a logging.Logger."""
        mock_request = Mock()
        mock_request.node.name = "test_something"

        context = PyTestContext(mock_request)
        logger = context.get_logger()

        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "test_something")

    def test_protocol_compliance(self):
        """Test that PyTestContext implements TestContext protocol."""
        mock_request = Mock()
        mock_request.node.name = "test_something"

        context = PyTestContext(mock_request)

        # Check that it's recognized as TestContext
        self.assertIsInstance(context, TestContext)


class TestTestContextProtocol(unittest.TestCase):
    """Tests for the TestContext protocol itself."""

    def test_protocol_attributes(self):
        """Test that TestContext protocol has expected methods."""
        # Get all required methods from the protocol
        methods = ['add_cleanup', 'fail', 'get_name', 'get_logger']

        for method in methods:
            self.assertTrue(
                hasattr(TestContext, method),
                f"TestContext protocol should have {method} method"
            )

    def test_custom_implementation_recognized(self):
        """Test that custom implementations are recognized as TestContext."""

        class CustomContext:
            def add_cleanup(self, fn: Callable[[], None]) -> None:
                pass

            def fail(self, msg: str) -> None:
                raise AssertionError(msg)

            def get_name(self) -> str:
                return "custom_test"

            def get_logger(self) -> logging.Logger:
                return logging.getLogger("custom_test")

        context = CustomContext()

        # Should be recognized as TestContext due to structural typing
        self.assertIsInstance(context, TestContext)


if __name__ == '__main__':
    unittest.main()
