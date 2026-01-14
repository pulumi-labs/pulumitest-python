"""Pytest implementation of TestContext.

This module provides PyTestContext, which integrates pulumitest with pytest
using the request fixture for cleanup and test metadata.
"""

from typing import Callable
import logging
import sys
from typing import TextIO

try:
    import pytest
    from _pytest.fixtures import FixtureRequest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    # Create dummy types for type checking when pytest is not installed
    class FixtureRequest:  # type: ignore[no-redef]
        pass

from .context import TestContext


class PyTestContext:
    """Pytest-native test context.

    Integrates with pytest's request fixture for cleanup and test metadata.
    Uses pytest.fail() for assertions and request.addfinalizer() for cleanup.

    This class should be instantiated with pytest's request fixture:

    Example:
        @pytest.fixture
        def pulumi_test(request):
            context = PyTestContext(request)
            test = PulumiTest(context, "my-program")
            return test

    Attributes:
        _request: Pytest fixture request object
        _logger: Logger for this test
    """

    _request: FixtureRequest
    _logger: logging.Logger

    def __init__(self, request: FixtureRequest):
        """Initialize from pytest request fixture.

        Args:
            request: Pytest fixture request object

        Raises:
            ImportError: If pytest is not installed
        """
        if not PYTEST_AVAILABLE:
            raise ImportError(
                "pytest is required to use PyTestContext. "
                "Install it with: pip install pytest"
            )

        self._request = request
        self._logger = self._setup_logger()

    def add_cleanup(self, fn: Callable[[], None]) -> None:
        """Register cleanup using pytest finalizer.

        Pytest finalizers run in LIFO order after the test completes,
        regardless of test success or failure.

        Args:
            fn: Cleanup function with no arguments
        """
        self._request.addfinalizer(fn)

    def fail(self, msg: str) -> None:
        """Fail test using pytest.fail().

        Args:
            msg: Failure message
        """
        pytest.fail(msg)

    def get_name(self) -> str:
        """Get test name from pytest request.

        Returns the test node name, which includes the full test path.

        Returns:
            Test name (e.g., "test_file.py::test_function")
        """
        return str(self._request.node.name)

    def get_logger(self) -> logging.Logger:
        """Get logger for this test.

        Returns a logger that integrates with pytest's output capturing.

        Returns:
            logging.Logger instance
        """
        return self._logger

    def _setup_logger(self) -> logging.Logger:
        """Setup logger with pytest integration.

        Creates a logger that writes to stdout, which pytest can capture
        and display appropriately.

        Returns:
            Configured logging.Logger
        """
        logger = logging.getLogger(self.get_name())
        logger.setLevel(logging.DEBUG)

        # Pytest captures logs automatically
        # Add stream handler for immediate output during test execution
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
