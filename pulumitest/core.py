"""Pytest-native core for Pulumi testing.

This module provides PulumiTest, a framework-agnostic test orchestrator
that uses TestContext protocol instead of unittest.TestCase.
"""

import sys
import os
from pulumi import automation as auto
import logging
from .opttest import opttest
from .context import TestContext
from .stack import Stack
from .copy import (
    copy_directory,
    copy_file,
    copy_symlink,
    create_if_not_exists,
    temp_dir_without_cleanup_on_failed_test
)
from pathlib import Path
from typing import Optional
from .result import PreviewResult, RefreshResult, UpdateResult


class PulumiTest:
    """Pytest-native Pulumi test orchestrator.

    This class provides core testing functionality without depending on
    unittest.TestCase. It uses the TestContext protocol to work with any
    test framework (pytest, unittest, or future frameworks).

    Example with pytest:
        @pytest.fixture
        def pulumi_test(request):
            context = PyTestContext(request)
            test = PulumiTest(context, "my-program")
            return test

    Example with unittest (via adapter):
        class MyTest(unittest.TestCase):
            def test_something(self):
                context = UnittestContext(self)
                test = PulumiTest(context, "my-program")
                test.up()

    Attributes:
        context: Test context for cleanup and logging
        working_dir: Directory containing Pulumi program
        options: Test options
        logger: Logger for this test
        _env_vars: Environment variables for workspace
        _stack: Stack instance (optional)
    """

    context: TestContext
    working_dir: str
    options: opttest.Options
    logger: logging.Logger
    _env_vars: dict[str, str]
    _stack: Optional[Stack]

    defaultStackName = "test"

    def __init__(
        self,
        context: TestContext,
        working_dir: str,
        *opts: opttest.Option,
        options: Optional[opttest.Options] = None
    ):
        """Initialize Pulumi test.

        Args:
            context: Test context for framework integration
            working_dir: Directory containing Pulumi program
            *opts: Variable options to apply
            options: Pre-configured options (overrides defaults)
        """
        self.context = context
        self.working_dir = working_dir

        # Setup options
        if options:
            self.options = options
        else:
            self.options = opttest.default_options()
        for opt in opts:
            opt.apply(self.options)

        # Setup logging via context
        self.logger = context.get_logger()

        # Track environment variables for coordination with external processes
        self._env_vars = {
            "PULUMI_BACKEND_URL": os.environ.get("PULUMI_BACKEND_URL", ""),
            "PULUMI_CONFIG_PASSPHRASE": self.options.config_passphrase or "correct horse battery staple",
        }

        # Copy to temp directory if not testing in place
        if not self.options.test_in_place:
            destination = self._create_temp_dir(*opts)
            self._copy_to(destination, *opts)
            self.working_dir = destination

        # Initialize stack
        self._stack = None
        self._pulumi_test_init()

    def _pulumi_test_init(self) -> None:
        """Initialize Pulumi workspace and stack.

        Creates Stack instance and registers cleanup with context.
        """
        self._stack = Stack(self.context, self.working_dir, self.options)

        # Register cleanup with context
        self.context.add_cleanup(self._cleanup)

    def _cleanup(self) -> None:
        """Cleanup function registered with context.

        Destroys and removes the stack.
        """
        if self._stack:
            self._stack.destroy_and_remove()

    @property
    def current_stack(self) -> auto.Stack:
        """Access the underlying Pulumi stack.

        Returns:
            Pulumi Stack instance

        Raises:
            RuntimeError: If stack is not initialized or skip_stack_create was used
        """
        if self._stack is None:
            raise RuntimeError("Stack not initialized")
        if self._stack.current_stack is None:
            raise RuntimeError("Stack not created (skip_stack_create option was used)")
        return self._stack.current_stack

    @property
    def local_workspace(self) -> auto.LocalWorkspace:
        """Access the underlying Pulumi workspace.

        Returns:
            Pulumi LocalWorkspace instance

        Raises:
            RuntimeError: If stack is not initialized
        """
        if self._stack is None:
            raise RuntimeError("Stack not initialized")
        return self._stack.local_workspace

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
        self.logger.info(f"Running pulumi up on stack: {self.current_stack.name}")
        result = self.current_stack.up()
        return UpdateResult(self.context, result)

    def preview(self) -> PreviewResult:
        """Run pulumi preview.

        Previews changes without applying them.

        Returns:
            PreviewResult with change summary

        Example:
            preview = test.preview()
            preview.has_no_changes()
        """
        self.logger.info(f"Running pulumi preview on stack: {self.current_stack.name}")
        result = self.current_stack.preview()
        return PreviewResult(self.context, result)

    def refresh(self) -> RefreshResult:
        """Run pulumi refresh.

        Refreshes stack state from actual infrastructure.

        Returns:
            RefreshResult with change summary

        Example:
            refresh = test.refresh()
            refresh.has_no_changes()
        """
        self.logger.info(f"Running pulumi refresh on stack: {self.current_stack.name}")
        result = self.current_stack.refresh()
        return RefreshResult(self.context, result)

    def destroy(self) -> auto.DestroyResult:
        """Run pulumi destroy.

        Destroys all stack resources.

        Returns:
            DestroyResult from Pulumi

        Example:
            test.destroy()
        """
        self.logger.info(f"Running pulumi destroy on stack: {self.current_stack.name}")
        return self.current_stack.destroy()

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
        self.logger.info(f"Updating source from {source_dir} to {self.working_dir}")

        source_path = Path(source_dir)
        working_path = Path(self.working_dir)

        # Files/directories to preserve (Pulumi state and config)
        preserve_paths = {'.pulumi', 'Pulumi.yaml', 'Pulumi.test.yaml'}

        # Recursively copy files from source to working dir, skipping preserved paths
        def copy_selective(src: Path, dst: Path) -> None:
            for entry in src.iterdir():
                # Skip preserved paths at the root level
                if entry.name in preserve_paths and src == source_path:
                    self.logger.info(f"Skipping preserved path: {entry.name}")
                    continue

                dest_path = dst / entry.name

                if entry.is_dir():
                    create_if_not_exists(str(dest_path), 0o755)
                    copy_selective(entry, dest_path)
                elif entry.is_symlink():
                    # Remove existing symlink/file if it exists
                    if dest_path.exists() or dest_path.is_symlink():
                        dest_path.unlink()
                    copy_symlink(str(entry), str(dest_path))
                else:
                    copy_file(str(entry), str(dest_path))

        try:
            copy_selective(source_path, working_path)
            self.logger.info(f"Successfully updated source from {source_dir}")
        except OSError as e:
            self.context.fail(f"Error updating source from {source_dir}: {e.strerror}")

    def add_environments(self, *environment_names: str) -> None:
        """Add ESC environments to stack.

        Args:
            *environment_names: Names of environments to add (e.g., "aws/dev")

        Example:
            test.add_environments("aws/pulumi-ce", "datadog/prod")
        """
        self.current_stack.add_environments(*environment_names)

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
        return self._env_vars.copy()

    def set_working_dir(self, working_dir: str) -> None:
        """Set working directory.

        Args:
            working_dir: Path to Pulumi program directory
        """
        self.working_dir = working_dir

    def copy_to_temp_dir(self, *opts: opttest.Option) -> "PulumiTest":
        """Copy program to temporary directory.

        Returns new PulumiTest instance for the copied program.
        Used to avoid temporary files being written to source directory.

        Args:
            *opts: Options to apply to the copy

        Returns:
            New PulumiTest instance with copied program

        Example:
            test = PulumiTest(context, "my-program")
            temp_test = test.copy_to_temp_dir()
            temp_test.up()
        """
        destination = self._create_temp_dir(*opts)
        return self.copy_to(destination, *opts)

    def copy_to(self, directory: str, *opts: opttest.Option) -> "PulumiTest":
        """Copy program to specified directory.

        Returns new PulumiTest instance for the copied program.

        Args:
            directory: Destination directory
            *opts: Options to apply to the copy

        Returns:
            New PulumiTest instance with copied program

        Example:
            test = PulumiTest(context, "my-program")
            copy = test.copy_to("/tmp/my-copy")
            copy.up()
        """
        options = self._copy_to(directory, *opts)
        opttest.test_in_place().apply(options)

        # Create new PulumiTest instance with the copied directory and options
        return PulumiTest(self.context, directory, options=options)

    def _create_temp_dir(self, *opts: opttest.Option) -> str:
        """Create temporary directory for test.

        Args:
            *opts: Options to apply

        Returns:
            Path to created temporary directory
        """
        options = self.options.copy()
        for opt in opts:
            opt.apply(options)

        temp_dir = temp_dir_without_cleanup_on_failed_test(
            self.logger,
            self.context,  # Pass context instead of unittest.TestCase
            "programDir",
            options.temp_dir
        )

        # Maintain the directory name in the temp dir as this might be used for stack naming
        source_base = Path(self.working_dir).name
        destination = Path(temp_dir) / source_base

        try:
            destination.mkdir(mode=0o755, exist_ok=False)
        except OSError as e:
            self.context.fail(f"error creating temp directory: {e.strerror}")

        return str(destination)

    def _copy_to(self, directory: str, *opts: opttest.Option) -> opttest.Options:
        """Internal copy implementation.

        Args:
            directory: Destination directory
            *opts: Options to apply

        Returns:
            Options object for the copy
        """
        try:
            copy_directory(self.working_dir, directory)
        except OSError as e:
            self.context.fail(f"error copying program to temp directory: {e.strerror}")

        options = self.options.copy()
        for opt in opts:
            opt.apply(options)

        return options
