"""Pytest plugin for Pulumi testing.

This module provides pytest fixtures for clean, native pytest integration with
Pulumi testing. It registers fixtures and custom markers for use in test files.

Usage:
    Install this package and pytest will automatically discover and load this plugin.
    Use fixtures in your tests:

    @pytest.mark.pulumi_program_dir("my-program")
    def test_deployment(pulumi_stack):
        outputs = pulumi_stack.current_stack.outputs()
        assert "bucket_name" in outputs

Available fixtures:
    - pulumi_test: Core test fixture with automatic cleanup
    - pulumi_stack: Auto-deploys stack before test, auto-destroys after
    - pulumi_program: Program fixture without auto-deployment
    - pulumi_test_factory: Factory for creating multiple test instances
    - pulumi_backend: Session-scoped backend configuration
    - pulumi_options: Configurable test options

Available markers:
    - @pytest.mark.pulumi_program_dir("path"): Specify program directory
    - @pytest.mark.pulumi_opts(opt1, opt2, ...): Specify test options
    - @pytest.mark.pulumi_skip_deploy: Skip auto-deployment for pulumi_stack
"""

import pytest
from typing import Generator, Callable, Any
from pathlib import Path
import os

from .core import PulumiTest
from .pytest_context import PyTestContext
from .opttest import opttest


def pytest_configure(config: Any) -> None:
    """Register custom markers for Pulumi testing.

    Args:
        config: Pytest configuration object
    """
    config.addinivalue_line(
        "markers",
        "pulumi_program_dir(path): Specify the directory containing the Pulumi program to test"
    )
    config.addinivalue_line(
        "markers",
        "pulumi_opts(*opts): Specify test options (e.g., opttest.test_in_place())"
    )
    config.addinivalue_line(
        "markers",
        "pulumi_skip_deploy: Skip automatic deployment when using pulumi_stack fixture"
    )


@pytest.fixture
def pulumi_options() -> opttest.Options:
    """Default options for Pulumi tests.

    Returns:
        Default Options instance

    Example:
        def test_with_custom_options(pulumi_options):
            pulumi_options.config_passphrase = "my-secret"
            # Use pulumi_options with pulumi_test_factory
    """
    return opttest.default_options()


@pytest.fixture(scope="session")
def pulumi_backend() -> dict[str, str]:
    """Session-scoped backend configuration.

    Provides environment variables for Pulumi backend. By default, uses
    the ambient backend configuration. Override this fixture to customize.

    Returns:
        Dictionary with PULUMI_BACKEND_URL and PULUMI_CONFIG_PASSPHRASE

    Example:
        @pytest.fixture(scope="session")
        def pulumi_backend():
            return {
                "PULUMI_BACKEND_URL": "file://./tmp/pulumi-state",
                "PULUMI_CONFIG_PASSPHRASE": "test-passphrase"
            }
    """
    return {
        "PULUMI_BACKEND_URL": os.environ.get("PULUMI_BACKEND_URL", ""),
        "PULUMI_CONFIG_PASSPHRASE": os.environ.get("PULUMI_CONFIG_PASSPHRASE", "correct horse battery staple"),
    }


def _get_program_dir(request: pytest.FixtureRequest) -> str:
    """Extract program directory from marker or fail.

    Args:
        request: Pytest fixture request

    Returns:
        Program directory path

    Raises:
        pytest.fail: If pulumi_program_dir marker is not found
    """
    marker = request.node.get_closest_marker("pulumi_program_dir")
    if marker is None:
        pytest.fail(
            "Test must be decorated with @pytest.mark.pulumi_program_dir('path/to/program'). "
            "This marker specifies the directory containing the Pulumi program to test."
        )
    if not marker.args:
        pytest.fail("pulumi_program_dir marker requires a path argument")

    return str(marker.args[0])


def _get_test_options(request: pytest.FixtureRequest) -> list[opttest.Option]:
    """Extract test options from marker.

    Args:
        request: Pytest fixture request

    Returns:
        List of Option instances
    """
    marker = request.node.get_closest_marker("pulumi_opts")
    if marker is None:
        return []
    return list(marker.args)


@pytest.fixture
def pulumi_test_factory(
    request: pytest.FixtureRequest,
    pulumi_options: opttest.Options
) -> Callable[[str, list[opttest.Option]], PulumiTest]:
    """Factory fixture for creating multiple PulumiTest instances.

    Useful when you need to test multiple programs or configurations in a
    single test.

    Args:
        request: Pytest fixture request
        pulumi_options: Default options to use

    Returns:
        Factory function that creates PulumiTest instances

    Example:
        def test_multiple_stacks(pulumi_test_factory):
            test1 = pulumi_test_factory("program1", [])
            test2 = pulumi_test_factory("program2", [opttest.test_in_place()])

            test1.up()
            test2.up()

            # Both will be automatically cleaned up
    """
    def create_test(
        program_dir: str,
        options: list[opttest.Option] | None = None
    ) -> PulumiTest:
        """Create a PulumiTest instance.

        Args:
            program_dir: Directory containing Pulumi program
            options: Optional list of test options

        Returns:
            PulumiTest instance with automatic cleanup
        """
        context = PyTestContext(request)
        opts = options if options is not None else []

        # Copy default options and apply custom opts
        test_options = pulumi_options.copy()
        for opt in opts:
            opt.apply(test_options)

        test = PulumiTest(context, program_dir, options=test_options)
        return test

    return create_test


@pytest.fixture
def pulumi_test(request: pytest.FixtureRequest) -> Generator[PulumiTest, None, None]:
    """Core Pulumi test fixture with automatic cleanup.

    Creates a PulumiTest instance for the program specified by the
    @pytest.mark.pulumi_program_dir marker. Does not automatically deploy
    the stack - use pulumi_stack for auto-deployment.

    Requires:
        @pytest.mark.pulumi_program_dir("path/to/program")

    Optional:
        @pytest.mark.pulumi_opts(opttest.test_in_place(), ...)

    Yields:
        PulumiTest instance

    Example:
        @pytest.mark.pulumi_program_dir("test_stack")
        def test_manual_deployment(pulumi_test):
            # Manual control over deployment
            result = pulumi_test.up()
            assert "bucket_name" in result.outputs

            preview = pulumi_test.preview()
            preview.has_no_changes()

            # Cleanup automatic via finalizer
    """
    program_dir = _get_program_dir(request)
    test_opts = _get_test_options(request)

    context = PyTestContext(request)
    test = PulumiTest(context, program_dir, *test_opts)

    yield test

    # Cleanup happens via context finalizers


@pytest.fixture
def pulumi_stack(request: pytest.FixtureRequest) -> Generator[PulumiTest, None, None]:
    """Pulumi stack fixture with automatic deployment and cleanup.

    Creates and deploys a Pulumi stack before the test runs, then automatically
    destroys and removes it after the test completes. This is the most convenient
    fixture for tests that just need a deployed stack.

    Skip auto-deployment with @pytest.mark.pulumi_skip_deploy

    Requires:
        @pytest.mark.pulumi_program_dir("path/to/program")

    Optional:
        @pytest.mark.pulumi_opts(opttest.test_in_place(), ...)
        @pytest.mark.pulumi_skip_deploy

    Yields:
        PulumiTest instance with deployed stack

    Example:
        @pytest.mark.pulumi_program_dir("test_stack")
        def test_deployed_stack(pulumi_stack):
            # Stack already deployed
            outputs = pulumi_stack.current_stack.outputs()
            assert "bucket_name" in outputs

            # Stack automatically destroyed after test

        @pytest.mark.pulumi_program_dir("test_stack")
        @pytest.mark.pulumi_skip_deploy
        def test_skip_deploy(pulumi_stack):
            # Stack created but not deployed
            pulumi_stack.up()  # Manual deployment
    """
    program_dir = _get_program_dir(request)
    test_opts = _get_test_options(request)

    context = PyTestContext(request)
    test = PulumiTest(context, program_dir, *test_opts)

    # Auto-deploy unless skip marker is present
    skip_deploy = request.node.get_closest_marker("pulumi_skip_deploy") is not None
    if not skip_deploy:
        test.up()

    yield test

    # Cleanup happens via context finalizers


@pytest.fixture
def pulumi_program(request: pytest.FixtureRequest) -> Generator[PulumiTest, None, None]:
    """Pulumi program fixture without automatic deployment.

    Alias for pulumi_test for semantic clarity. Use this when you want to
    emphasize that you're testing the program setup without auto-deployment.

    Requires:
        @pytest.mark.pulumi_program_dir("path/to/program")

    Optional:
        @pytest.mark.pulumi_opts(opttest.test_in_place(), ...)

    Yields:
        PulumiTest instance

    Example:
        @pytest.mark.pulumi_program_dir("test_stack")
        def test_program_setup(pulumi_program):
            # Test program without deployment
            assert pulumi_program.working_dir.endswith("test_stack")
            env_vars = pulumi_program.get_env_vars()
            assert "PULUMI_CONFIG_PASSPHRASE" in env_vars
    """
    # This is just an alias for pulumi_test with clearer semantics
    program_dir = _get_program_dir(request)
    test_opts = _get_test_options(request)

    context = PyTestContext(request)
    test = PulumiTest(context, program_dir, *test_opts)

    yield test

    # Cleanup happens via context finalizers


# Export public API
__all__ = [
    "pytest_configure",
    "pulumi_test",
    "pulumi_stack",
    "pulumi_program",
    "pulumi_test_factory",
    "pulumi_options",
    "pulumi_backend",
]
