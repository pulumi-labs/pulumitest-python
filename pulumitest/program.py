"""Framework-independent Pulumi program wrapper.

This module provides PulumiProgram, a pure Pulumi Automation API wrapper with
ZERO test framework dependencies. It can be used anywhere - in tests, scripts,
or any Python code that needs to work with Pulumi infrastructure.

Key features:
- No test framework coupling (no unittest, no pytest, nothing)
- Returns cleanup callback for manual registration
- Full Pulumi operations: up, preview, refresh, destroy, etc.
- Composable and reusable

Example usage in pytest:
    def test_my_stack(request):
        program = PulumiProgram("test_stack")
        request.addfinalizer(program.cleanup)  # Register cleanup

        result = program.up()
        assert "bucket_name" in result.outputs

Example usage in unittest:
    class TestStack(unittest.TestCase):
        def test_deployment(self):
            program = PulumiProgram("test_stack")
            self.addCleanup(program.cleanup)  # Register cleanup

            program.up()

Example usage standalone:
    program = PulumiProgram("test_stack")
    try:
        program.up()
    finally:
        program.cleanup()
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Callable
from pulumi import automation as auto

from .opttest import opttest
from .result import UpdateResult, PreviewResult, RefreshResult
from .copy import (
    copy_directory,
    copy_file,
    copy_symlink,
    create_if_not_exists,
)
from .context import TestContext


class _MinimalContext:
    """Minimal TestContext implementation for standalone usage.

    This class implements just enough of the TestContext protocol to work
    with result classes. It raises RuntimeError on test failures instead of
    using a test framework's assertion mechanism.
    """

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def add_cleanup(self, fn: Callable[[], None]) -> None:
        """No-op: cleanup must be managed manually in standalone mode."""
        pass

    def fail(self, msg: str) -> None:
        """Fail by raising RuntimeError."""
        raise RuntimeError(msg)

    def get_name(self) -> str:
        """Return a generic name."""
        return "PulumiProgram"

    def get_logger(self) -> logging.Logger:
        """Return the logger."""
        return self._logger


class PulumiProgram:
    """Framework-independent Pulumi program wrapper.

    This class wraps Pulumi Automation API operations without any test
    framework dependencies. It provides a cleanup callback that can be
    registered with any test framework or called manually.

    All operations and options from the original pulumitest are available,
    but without requiring unittest.TestCase or pytest fixtures.

    Attributes:
        working_dir: Directory containing Pulumi program
        options: Test options
        logger: Logger for this program
        current_stack: Pulumi stack instance (after initialization)
        local_workspace: Pulumi workspace instance (after initialization)
    """

    working_dir: str
    options: opttest.Options
    logger: logging.Logger
    current_stack: auto.Stack | None
    local_workspace: auto.LocalWorkspace | None
    _env_vars: dict[str, str]
    _cleanup_registered: bool

    defaultStackName = "test"

    def __init__(
        self,
        working_dir: str,
        *opts: opttest.Option,
        options: Optional[opttest.Options] = None,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize Pulumi program.

        Args:
            working_dir: Directory containing Pulumi program
            *opts: Variable options to apply
            options: Pre-configured options (overrides defaults)
            logger: Optional logger (creates default if not provided)

        Example:
            # Basic usage
            program = PulumiProgram("test_stack")

            # With options
            program = PulumiProgram(
                "test_stack",
                opttest.test_in_place(),
                opttest.skip_install()
            )

            # With custom logger
            program = PulumiProgram(
                "test_stack",
                logger=logging.getLogger("my_test")
            )
        """
        self.working_dir = working_dir

        # Setup options
        if options:
            self.options = options
        else:
            self.options = opttest.default_options()
        for opt in opts:
            opt.apply(self.options)

        # Setup logging
        if logger:
            self.logger = logger
        else:
            self.logger = self._create_default_logger()

        # Track environment variables
        self._env_vars = {
            "PULUMI_BACKEND_URL": os.environ.get("PULUMI_BACKEND_URL", ""),
            "PULUMI_CONFIG_PASSPHRASE": self.options.config_passphrase or "correct horse battery staple",
        }

        # Copy to temp directory if not testing in place
        if not self.options.test_in_place:
            destination = self._create_temp_dir()
            self._copy_to_internal(destination)
            self.working_dir = destination

        # Initialize stack
        self.current_stack = None
        self.local_workspace = None
        self._cleanup_registered = False
        self._init_stack()

    def _create_default_logger(self) -> logging.Logger:
        """Create default logger with stdout handler."""
        logger = logging.getLogger(f"PulumiProgram-{id(self)}")
        logger.setLevel(logging.DEBUG)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
        handler.setFormatter(formatter)

        if not logger.handlers:
            logger.addHandler(handler)

        return logger

    def _create_temp_dir(self) -> str:
        """Create temporary directory for program."""
        import uuid

        if self.options.temp_dir:
            base_dir = Path(self.options.temp_dir)
            base_dir.mkdir(parents=True, exist_ok=True)
        else:
            base_dir = Path.cwd() / "tmp"
            base_dir.mkdir(exist_ok=True)

        temp_path = base_dir / f"programDir_{uuid.uuid4().hex[:8]}"
        self.logger.info(f"Creating temp directory {temp_path.name}")

        # Maintain directory name for stack naming
        source_base = Path(self.working_dir).name
        destination = temp_path / source_base
        destination.mkdir(mode=0o755, parents=True, exist_ok=True)

        return str(destination)

    def _copy_to_internal(self, directory: str) -> None:
        """Internal copy implementation."""
        try:
            copy_directory(self.working_dir, directory)
        except OSError as e:
            raise RuntimeError(f"Error copying program to {directory}: {e.strerror}")

    def _init_stack(self) -> None:
        """Initialize Pulumi workspace and stack."""
        self.logger.info("Creating local workspace...")
        self.local_workspace = auto.LocalWorkspace(work_dir=self.working_dir)

        # Run install unless skipped
        if not self.options.skip_install:
            self.logger.info("Running pulumi install...")
            self.local_workspace.install()

        # Create or select stack unless skipped
        if not self.options.skip_stack_create:
            stack_name = self.options.stack_name or self.defaultStackName
            self.logger.info(f"Running pulumi stack init... (stack: {stack_name})")
            self.current_stack = auto.create_or_select_stack(
                stack_name,
                work_dir=self.working_dir
            )
        else:
            self.logger.info("Skipping stack creation (skip_stack_create=True)")

    def cleanup(self) -> None:
        """Cleanup function to destroy and remove stack.

        This method should be registered with your test framework's cleanup
        mechanism, or called manually in a finally block.

        Examples:
            # Pytest
            request.addfinalizer(program.cleanup)

            # Unittest
            self.addCleanup(program.cleanup)

            # Manual
            try:
                program.up()
            finally:
                program.cleanup()
        """
        if self.current_stack is not None:
            self.logger.info("Running pulumi destroy and removing stack...")
            try:
                self.current_stack.destroy(remove=True)
            except Exception as e:
                self.logger.error(f"Error during cleanup: {e}")
        else:
            self.logger.info("No current stack, skipping destroy...")

    def up(self) -> UpdateResult:
        """Run pulumi up.

        Returns:
            UpdateResult with outputs and summary
        """
        if self.current_stack is None:
            raise RuntimeError("Stack not initialized")

        self.logger.info(f"Running pulumi up on stack: {self.current_stack.name}")
        result = self.current_stack.up()

        # Create a minimal context object for UpdateResult
        return UpdateResult(self._create_result_context(), result)

    def preview(self) -> PreviewResult:
        """Run pulumi preview.

        Returns:
            PreviewResult with change summary
        """
        if self.current_stack is None:
            raise RuntimeError("Stack not initialized")

        self.logger.info(f"Running pulumi preview on stack: {self.current_stack.name}")
        result = self.current_stack.preview()

        return PreviewResult(self._create_result_context(), result)

    def refresh(self) -> RefreshResult:
        """Run pulumi refresh.

        Returns:
            RefreshResult with change summary
        """
        if self.current_stack is None:
            raise RuntimeError("Stack not initialized")

        self.logger.info(f"Running pulumi refresh on stack: {self.current_stack.name}")
        result = self.current_stack.refresh()

        return RefreshResult(self._create_result_context(), result)

    def destroy(self) -> auto.DestroyResult:
        """Run pulumi destroy.

        Returns:
            DestroyResult from Pulumi
        """
        if self.current_stack is None:
            raise RuntimeError("Stack not initialized")

        self.logger.info(f"Running pulumi destroy on stack: {self.current_stack.name}")
        return self.current_stack.destroy()

    def update_source(self, source_dir: str) -> None:
        """Update working directory from source.

        Replaces program files while maintaining stack state.

        Args:
            source_dir: Directory containing new program files
        """
        self.logger.info(f"Updating source from {source_dir} to {self.working_dir}")

        source_path = Path(source_dir)
        working_path = Path(self.working_dir)

        # Files/directories to preserve
        preserve_paths = {'.pulumi', 'Pulumi.yaml', 'Pulumi.test.yaml'}

        def copy_selective(src: Path, dst: Path) -> None:
            for entry in src.iterdir():
                if entry.name in preserve_paths and src == source_path:
                    self.logger.info(f"Skipping preserved path: {entry.name}")
                    continue

                dest_path = dst / entry.name

                if entry.is_dir():
                    create_if_not_exists(str(dest_path), 0o755)
                    copy_selective(entry, dest_path)
                elif entry.is_symlink():
                    if dest_path.exists() or dest_path.is_symlink():
                        dest_path.unlink()
                    copy_symlink(str(entry), str(dest_path))
                else:
                    copy_file(str(entry), str(dest_path))

        try:
            copy_selective(source_path, working_path)
            self.logger.info(f"Successfully updated source from {source_dir}")
        except OSError as e:
            raise RuntimeError(f"Error updating source from {source_dir}: {e.strerror}")

    def add_environments(self, *environment_names: str) -> None:
        """Add ESC environments to stack.

        Args:
            *environment_names: Names of environments to add
        """
        if self.current_stack is None:
            raise RuntimeError("Stack not initialized")

        self.current_stack.add_environments(*environment_names)

    def get_env_vars(self) -> dict[str, str]:
        """Get environment variables for this workspace.

        Returns:
            Dictionary with PULUMI_BACKEND_URL and PULUMI_CONFIG_PASSPHRASE
        """
        return self._env_vars.copy()

    def set_working_dir(self, working_dir: str) -> None:
        """Set working directory.

        Args:
            working_dir: Path to Pulumi program directory
        """
        self.working_dir = working_dir

    def copy_to_temp_dir(self, *opts: opttest.Option) -> "PulumiProgram":
        """Copy program to temporary directory.

        Args:
            *opts: Options to apply to the copy

        Returns:
            New PulumiProgram instance with copied program
        """
        destination = self._create_temp_dir()
        return self.copy_to(destination, *opts)

    def copy_to(self, directory: str, *opts: opttest.Option) -> "PulumiProgram":
        """Copy program to specified directory.

        Args:
            directory: Destination directory
            *opts: Options to apply to the copy

        Returns:
            New PulumiProgram instance with copied program
        """
        self._copy_to_internal(directory)

        options = self.options.copy()
        for opt in opts:
            opt.apply(options)
        opttest.test_in_place().apply(options)

        return PulumiProgram(directory, options=options, logger=self.logger)

    def _create_result_context(self) -> TestContext:
        """Create a minimal context object for result classes.

        Result classes expect a TestContext implementation.
        We create a minimal one that raises RuntimeError on fail.
        """
        return _MinimalContext(self.logger)


__all__ = ["PulumiProgram"]
