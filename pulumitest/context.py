"""Test framework abstraction via Protocol.

This module defines the TestContext protocol which abstracts test framework
operations, allowing pulumitest to work with any test framework (pytest, unittest,
or future frameworks).
"""

from typing import Protocol, Callable, runtime_checkable
import logging


@runtime_checkable
class TestContext(Protocol):
    """Protocol for test framework abstraction.

    This protocol defines the interface that test framework implementations
    must provide to work with pulumitest. By using a Protocol instead of
    an ABC, implementations don't need to explicitly inherit from this class.

    Implementations:
        - PyTestContext: Pytest integration using request.addfinalizer()
        - UnittestContext: Unittest integration using TestCase.addCleanup()

    Example:
        class MyTestContext:
            def add_cleanup(self, fn: Callable[[], None]) -> None:
                # Register cleanup function
                pass

            def fail(self, msg: str) -> None:
                # Fail the test
                raise AssertionError(msg)

            def get_name(self) -> str:
                return "my_test"

            def get_logger(self) -> logging.Logger:
                return logging.getLogger("my_test")
    """

    def add_cleanup(self, fn: Callable[[], None]) -> None:
        """Register a cleanup function to run after test completion.

        The cleanup function will be called regardless of test success or failure.
        Multiple cleanup functions can be registered and will be called in LIFO
        order (last registered, first called).

        Args:
            fn: Cleanup function with no arguments and no return value.
                This function should not raise exceptions.

        Example:
            def cleanup_resources():
                print("Cleaning up resources")

            context.add_cleanup(cleanup_resources)
        """
        ...

    def fail(self, msg: str) -> None:
        """Fail the test with a message.

        This method should cause the test to fail immediately with the given
        message. The implementation should use the framework's native failure
        mechanism (pytest.fail(), TestCase.fail(), etc.).

        Args:
            msg: Failure message describing why the test failed

        Raises:
            AssertionError or framework-specific exception

        Example:
            if not condition:
                context.fail("Expected condition to be true")
        """
        ...

    def get_name(self) -> str:
        """Get the current test name.

        Returns the name of the currently executing test. The format may vary
        by framework:
        - pytest: Full test path (e.g., "test_file.py::test_function")
        - unittest: Method name (e.g., "test_function")

        Returns:
            Test name as a string

        Example:
            logger = logging.getLogger(context.get_name())
        """
        ...

    def get_logger(self) -> logging.Logger:
        """Get logger for this test.

        Returns a logger configured for the current test. The logger should
        be properly integrated with the test framework's output capturing.

        Returns:
            logging.Logger instance for this test

        Example:
            logger = context.get_logger()
            logger.info("Starting test")
        """
        ...
