"""Unittest implementation of TestContext.

This module provides UnittestContext, which wraps unittest.TestCase to
provide the TestContext interface for compatibility with unittest-based tests.
"""

from typing import Callable
import logging
import sys
from typing import TextIO
import unittest

from .context import TestContext


class UnittestContext:
    """Unittest implementation of test context.

    Wraps unittest.TestCase to provide the TestContext protocol interface.
    This allows the core pulumitest framework to work with unittest-based tests.

    Example:
        class MyTest(unittest.TestCase):
            def test_something(self):
                context = UnittestContext(self)
                test = PulumiTest(context, "my-program")
                test.up()

    Attributes:
        _test_case: Unittest TestCase instance
        _logger: Logger for this test
    """

    _test_case: unittest.TestCase
    _logger: logging.Logger

    def __init__(self, test_case: unittest.TestCase):
        """Initialize from unittest TestCase.

        Args:
            test_case: Unittest TestCase instance (typically 'self' from a test method)
        """
        self._test_case = test_case
        self._logger = self._setup_logger()

    def add_cleanup(self, fn: Callable[[], None]) -> None:
        """Register cleanup using TestCase.addCleanup().

        Unittest cleanup functions run in LIFO order after the test completes.
        They run regardless of test success or failure.

        Args:
            fn: Cleanup function with no arguments
        """
        self._test_case.addCleanup(fn)

    def fail(self, msg: str) -> None:
        """Fail test using TestCase.fail().

        Args:
            msg: Failure message
        """
        self._test_case.fail(msg)

    def get_name(self) -> str:
        """Get test name from TestCase.

        Returns the test method name.

        Returns:
            Test method name (e.g., "test_something")
        """
        return self._test_case._testMethodName

    def get_logger(self) -> logging.Logger:
        """Get logger for this test.

        Returns a logger that writes to stdout for unittest compatibility.

        Returns:
            logging.Logger instance
        """
        return self._logger

    def _setup_logger(self) -> logging.Logger:
        """Setup logger for unittest.

        Creates a logger that writes to stdout, compatible with unittest's
        output capturing.

        Returns:
            Configured logging.Logger
        """
        logger = logging.getLogger(self.get_name())
        logger.setLevel(logging.DEBUG)

        # Add stream handler for stdout
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)

        # Use a simple format
        formatter = logging.Formatter(
            '%(levelname)s - %(name)s - %(message)s'
        )
        handler.setFormatter(formatter)

        # Only add handler if not already present
        if not logger.handlers:
            logger.addHandler(handler)

        return logger
