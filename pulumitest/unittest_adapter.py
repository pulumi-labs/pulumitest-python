"""Unittest adapter for backward compatibility.

This module provides PulumiTestProgram, a backward-compatible wrapper around
the pytest-native PulumiTest core. It maintains the exact same API as the
original unittest-based implementation, ensuring existing tests continue
working without modification.

The adapter wraps unittest.TestCase with UnittestContext and delegates all
operations to the framework-agnostic PulumiTest core.

Example (existing unittest code works unchanged):
    class TestStack(unittest.TestCase):
        def test_deployment(self):
            test = PulumiTestProgram(self, "my-program")
            test.up()
            preview = test.preview()
            preview.has_no_changes()
            # Cleanup automatic via addCleanup
"""

import unittest
import logging
from typing import Optional
from pulumi import automation as auto

from .core import PulumiTest
from .unittest_context import UnittestContext
from .opttest import opttest
from .result import UpdateResult, PreviewResult, RefreshResult


class PulumiTestProgram:
    """Unittest adapter wrapping PulumiTest core.

    Provides backward compatibility with the original unittest-based API.
    This class is a thin wrapper that converts unittest.TestCase to
    UnittestContext and delegates all operations to PulumiTest.

    All methods maintain the exact same signatures and behavior as the
    original implementation to ensure 100% backward compatibility.

    Example:
        class MyTest(unittest.TestCase):
            def test_something(self):
                test = PulumiTestProgram(self, "test_stack")
                test.up()
                # All existing code works unchanged
    """

    _core: PulumiTest
    defaultStackName = "test"

    def __init__(
        self,
        t: unittest.TestCase,
        working_dir: str,
        *opts: opttest.Option,
        options: Optional[opttest.Options] = None
    ):
        """Initialize Pulumi test program for unittest.

        Args:
            t: unittest.TestCase instance
            working_dir: Directory containing Pulumi program
            *opts: Variable options to apply
            options: Pre-configured options (overrides defaults)

        Example:
            def test_deployment(self):
                test = PulumiTestProgram(self, "test_stack")
                test.add_environments("aws/pulumi-ce")
                test.up()
        """
        # Wrap TestCase with UnittestContext
        context = UnittestContext(t)

        # Create core PulumiTest instance
        self._core = PulumiTest(context, working_dir, *opts, options=options)

    @property
    def working_dir(self) -> str:
        """Get working directory."""
        return self._core.working_dir

    @property
    def options(self) -> opttest.Options:
        """Get test options."""
        return self._core.options

    @property
    def logger(self) -> logging.Logger:
        """Get logger for this test."""
        return self._core.logger

    @property
    def current_stack(self) -> auto.Stack:
        """Access the underlying Pulumi stack.

        Returns:
            Pulumi Stack instance

        Raises:
            RuntimeError: If stack is not initialized
        """
        return self._core.current_stack

    @property
    def local_workspace(self) -> auto.LocalWorkspace:
        """Access the underlying Pulumi workspace.

        Returns:
            Pulumi LocalWorkspace instance

        Raises:
            RuntimeError: If stack is not initialized
        """
        return self._core.local_workspace

    def up(self) -> UpdateResult:
        """Run pulumi up.

        Deploys the stack and returns the result.

        Returns:
            UpdateResult with outputs and summary

        Example:
            result = test.up()
            outputs = result.outputs
            assert "bucket_name" in outputs
        """
        return self._core.up()

    def preview(self) -> PreviewResult:
        """Run pulumi preview.

        Previews changes without applying them.

        Returns:
            PreviewResult with change summary

        Example:
            preview = test.preview()
            preview.has_no_changes()
        """
        return self._core.preview()

    def refresh(self) -> RefreshResult:
        """Run pulumi refresh.

        Refreshes stack state from actual infrastructure.

        Returns:
            RefreshResult with change summary

        Example:
            refresh = test.refresh()
            refresh.has_no_changes()
        """
        return self._core.refresh()

    def destroy(self) -> auto.DestroyResult:
        """Run pulumi destroy.

        Destroys all stack resources.

        Returns:
            DestroyResult from Pulumi

        Example:
            test.destroy()
        """
        return self._core.destroy()

    def update_source(self, source_dir: str) -> None:
        """Update working directory from source.

        Replaces program files while maintaining stack state. This is
        critical for provider-agnostic drift testing:
        1. Deploy with original code
        2. Switch to drifted code and deploy
        3. Switch back to original code while preserving drift in state

        Args:
            source_dir: Directory containing new program files

        Example:
            test.update_source("original")
            test.up()
            saved_state = test.current_stack.export_stack()
            test.update_source("drifted")
            test.up()
            test.current_stack.import_stack(saved_state)
            test.update_source("original")
        """
        self._core.update_source(source_dir)

    def add_environments(self, *environment_names: str) -> None:
        """Add ESC environments to stack.

        Args:
            *environment_names: Names of environments to add (e.g., "aws/dev")

        Example:
            test.add_environments("aws/pulumi-ce", "datadog/prod")
        """
        self._core.add_environments(*environment_names)

    def get_env_vars(self) -> dict[str, str]:
        """Get environment variables for this workspace.

        Useful for coordinating between the test framework and external
        processes to ensure they use the same backend and configuration.

        Returns:
            Dictionary with PULUMI_BACKEND_URL and PULUMI_CONFIG_PASSPHRASE

        Example:
            env_vars = test.get_env_vars()
            subprocess.run(["pulumi", "preview"], env=env_vars)
        """
        return self._core.get_env_vars()

    def set_working_dir(self, working_dir: str) -> None:
        """Set working directory.

        Args:
            working_dir: Path to Pulumi program directory
        """
        self._core.set_working_dir(working_dir)

    def copy_to_temp_dir(self, *opts: opttest.Option) -> "PulumiTestProgram":
        """Copy program to temporary directory.

        Returns new PulumiTestProgram instance for the copied program.
        Used to avoid temporary files being written to source directory.

        Args:
            *opts: Options to apply to the copy

        Returns:
            New PulumiTestProgram instance with copied program

        Example:
            test = PulumiTestProgram(self, "my-program")
            temp_test = test.copy_to_temp_dir()
            temp_test.up()
        """
        # Copy using core
        copied_core = self._core.copy_to_temp_dir(*opts)

        # Create new adapter wrapping the copied core
        # We need to extract the TestCase from the UnittestContext
        adapter = PulumiTestProgram.__new__(PulumiTestProgram)
        adapter._core = copied_core
        return adapter

    def copy_to(self, directory: str, *opts: opttest.Option) -> "PulumiTestProgram":
        """Copy program to specified directory.

        Returns new PulumiTestProgram instance for the copied program.

        Args:
            directory: Destination directory
            *opts: Options to apply to the copy

        Returns:
            New PulumiTestProgram instance with copied program

        Example:
            test = PulumiTestProgram(self, "my-program")
            copy = test.copy_to("/tmp/my-copy")
            copy.up()
        """
        # Copy using core
        copied_core = self._core.copy_to(directory, *opts)

        # Create new adapter wrapping the copied core
        adapter = PulumiTestProgram.__new__(PulumiTestProgram)
        adapter._core = copied_core
        return adapter

    # Legacy method names for compatibility
    def destroyAndRemoveStack(self) -> None:
        """Legacy method for destroying and removing stack.

        DEPRECATED: This method is maintained for backward compatibility.
        Cleanup now happens automatically via TestCase.addCleanup().

        Note: This method is called automatically during cleanup and
        should not be called directly in new code.
        """
        if self._core._stack:
            self._core._stack.destroy_and_remove()

    def pulumi_test_init(self) -> None:
        """Legacy initialization method.

        DEPRECATED: This method is maintained for backward compatibility.
        Initialization now happens in __init__().

        Note: This method is a no-op as initialization is handled
        automatically during construction.
        """
        # No-op: initialization already done in __init__ via core
        pass


# Export public API
__all__ = ["PulumiTestProgram"]
