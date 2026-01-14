import sys
import os
from pulumi import automation as auto
import unittest
import logging
from .opttest import opttest
from .copy import (
    copy_directory,
    copy_file,
    copy_symlink,
    create_if_not_exists,
    temp_dir_without_cleanup_on_failed_test
)
from pathlib import Path
from typing import Self
from .result import PreviewResult, RefreshResult, UpdateResult

class PulumiTestProgram:
    current_stack: auto.Stack
    working_dir: str
    logger: logging.Logger
    stream_handler: logging.StreamHandler
    t: unittest.TestCase
    options: opttest.Options
    _env_vars: dict

    defaultStackName = "test"        
    
    def destroyAndRemoveStack(self):
        if self.current_stack is not None:
            self.logger.info("Running pulumi destroy and removing stack...")
            self.current_stack.destroy(remove=True)
            self.logger.removeHandler(self.stream_handler)
        else:
            self.logger.info("No current stack, skipping destroy...")

    def __init__(self, t: unittest.TestCase, working_dir: str, *opts: opttest.Option, options: opttest.Options = None):
        if options:
            self.options = options
        else:
            self.options = opttest.default_options()
        for opt in opts:
            opt.apply(self.options)

        self.logger = logging.getLogger(t._testMethodName)
        self.logger.setLevel(logging.DEBUG)
        self.stream_handler = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(self.stream_handler)

        self.t = t
        self.set_working_dir(working_dir)

        # Track environment variables for coordination with external processes
        self._env_vars = {
            "PULUMI_BACKEND_URL": os.environ.get("PULUMI_BACKEND_URL", ""),
            "PULUMI_CONFIG_PASSPHRASE": self.options.config_passphrase or "correct horse battery staple",
        }

        if not self.options.test_in_place:
            destination = self._create_temp_dir(*opts)
            self._copy_to(destination, *opts)
            self.set_working_dir(destination)

        self.pulumi_test_init()

    def pulumi_test_init(self):
        self.logger.info("Creating local workspace...")
        self.local_workspace = auto.LocalWorkspace(work_dir=self.working_dir)
        self.logger.info("Running pulumi install...")
        self.local_workspace.install()
        self.logger.info("Running pulumi stack init...")
        self.current_stack = auto.create_or_select_stack(self.defaultStackName, work_dir=self.working_dir)
        self.t.addCleanup(self.destroyAndRemoveStack)

    def up(self):
        self.logger.info(f"Running pulumi up on stack: {self.current_stack.name}")
        result = self.current_stack.up()
        return UpdateResult(self.t, result)
    
    def preview(self):
        self.logger.info(f"Running pulumi preview on stack: {self.current_stack.name}")
        result = self.current_stack.preview()
        return PreviewResult(self.t, result)
    
    def destroy(self):
        self.logger.info(f"Running pulumi destroy on stack: {self.current_stack.name}")
        return self.current_stack.destroy()
    
    def refresh(self):
        self.logger.info(f"Running pulumi refresh on stack: {self.current_stack.name}")
        result = self.current_stack.refresh()
        return RefreshResult(self.t, result)

    def update_source(self, source_dir: str):
        """
        Update the working directory's program files from source_dir.
        Replaces program files while maintaining stack and state.

        This is critical for provider-agnostic drift testing where you need to:
        1. Deploy with original code
        2. Switch to drifted code and deploy
        3. Switch back to original code while preserving drift in state

        Args:
            source_dir: Directory containing the new program files to copy
        """
        self.logger.info(f"Updating source from {source_dir} to {self.working_dir}")

        source_path = Path(source_dir)
        working_path = Path(self.working_dir)

        # Files/directories to preserve (Pulumi state and config)
        preserve_paths = {'.pulumi', 'Pulumi.yaml', 'Pulumi.test.yaml'}

        # Recursively copy files from source to working dir, skipping preserved paths
        def copy_selective(src: Path, dst: Path):
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
            self.t.fail(f"Error updating source from {source_dir}: {e.strerror}")

    def add_environments(self, *environment_names: str):
        self.current_stack.add_environments(*environment_names)

    def get_env_vars(self) -> dict:
        """
        Return environment variables for this workspace.

        This is useful for coordinating between the test framework and external processes
        (like Claude or bash tools) to ensure they use the same backend and configuration.

        Returns:
            Dictionary containing PULUMI_BACKEND_URL and PULUMI_CONFIG_PASSPHRASE
        """
        return self._env_vars.copy()

    def set_working_dir(self, working_dir: str):
        self.working_dir = working_dir
    
    def copy_to_temp_dir(self, *opts: opttest.Option) -> Self:
        """Copy the program to a temporary directory.
        Returns a new PulumiTest instance for the copied program.
        This is used to avoid temporary files being written to the source directory.
        """
        destination = self._create_temp_dir(*opts)
        
        return self.copy_to(destination, *opts)
    
    def _create_temp_dir(self, *opts: opttest.Option) -> str:
        options = self.options.copy()
        for opt in opts:
            opt.apply(options)
        
        temp_dir = temp_dir_without_cleanup_on_failed_test(self.logger, self.t, "programDir", options.temp_dir)
        
        # Maintain the directory name in the temp dir as this might be used for stack naming
        source_base = Path(self.working_dir).name
        destination = Path(temp_dir) / source_base
        
        try:
            destination.mkdir(mode=0o755, exist_ok=False)
        except OSError as e:
            self.t.fail(f"error creating temp directory: {e.strerror}")
        
        return str(destination)
    
    def copy_to(self, directory: str, *opts: opttest.Option) -> Self:
        """Copy the program to the specified directory.
        Returns a new PulumiTest instance for the copied program.
        """
        options = self._copy_to(directory, *opts)
        opttest.test_in_place().apply(options)
        
        # Create new PulumiTest instance with the copied directory and options
        return PulumiTestProgram(self.t, directory, options=options)

    def _copy_to(self, directory: str, *opts: opttest.Option) -> opttest.Options:
        try:
            copy_directory(self.working_dir, directory)
        except OSError as e:
            self.t.fail(f"error copying program to temp directory: {e.strerror}")
        
        options = self.options.copy()
        for opt in opts:
            opt.apply(options)
        
        return options