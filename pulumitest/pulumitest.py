import sys
from pulumi import automation as auto
import unittest
import logging
from .opttest import opttest
from .copy import (
    copy_directory, 
    temp_dir_without_cleanup_on_failed_test
)
from pathlib import Path
from typing import Self

class PulumiTestProgram:
    current_stack: auto.Stack
    working_dir: str
    logger: logging.Logger
    stream_handler: logging.StreamHandler
    t: unittest.TestCase
    options: opttest.Options

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

        if not self.options.test_in_place:
            destination = self._copy_to_temp_dir(*opts)
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
        # self.t = t
        self.t.addCleanup(self.destroyAndRemoveStack)

    def up(self):
        self.logger.info(f"Running pulumi up on stack: {self.current_stack.name}")
        return self.current_stack.up()
    
    def preview(self):
        self.logger.info(f"Running pulumi preview on stack: {self.current_stack.name}")
        return self.current_stack.preview()
    
    def destroy(self):
        self.logger.info(f"Running pulumi destroy on stack: {self.current_stack.name}")
        return self.current_stack.destroy()
    
    def refresh(self):
        self.logger.info(f"Running pulumi refresh on stack: {self.current_stack.name}")
        return self.current_stack.refresh()

    def add_environments(self, *environment_names: str):
        self.current_stack.add_environments(*environment_names)
    
    def set_working_dir(self, working_dir: str):
        self.working_dir = working_dir

    @classmethod
    def copy_to_temp_dir(cls, pulumi_test: Self, *opts: opttest.Option) -> Self:
        """Copy the program to a temporary directory.
        Returns a new PulumiTest instance for the copied program.
        This is used to avoid temporary files being written to the source directory.
        """
        # options = pulumi_test.options.copy()
        # for opt in opts:
        #     opt.apply(options)
        
        # temp_dir = temp_dir_without_cleanup_on_failed_test(pulumi_test.logger, pulumi_test.t, "programDir", options.temp_dir)
        
        # # Maintain the directory name in the temp dir as this might be used for stack naming
        # source_base = Path(pulumi_test.working_dir).name
        # destination = Path(temp_dir) / source_base
        
        # try:
        #     destination.mkdir(mode=0o755, exist_ok=False)
        # except OSError as e:
        #     pulumi_test.t.fail(f"error creating temp directory: {e.strerror}")
        destination = pulumi_test._copy_to_temp_dir(*opts)
        
        return cls.copy_to(pulumi_test, destination, *opts)
    
    def _copy_to_temp_dir(self, *opts: opttest.Option) -> str:
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
    
    @classmethod
    def copy_to(cls, pulumi_test: Self, directory: str, *opts: opttest.Option) -> Self:
        """Copy the program to the specified directory.
        Returns a new PulumiTest instance for the copied program.
        """
        options = pulumi_test._copy_to(directory, *opts)
        
        # Create new PulumiTest instance with the copied directory and options
        new_test = cls(pulumi_test.t, directory, opttest.test_in_place(), options=options)
        new_test.options = options
        return new_test

    def _copy_to(self, directory: str, *opts: opttest.Option) -> opttest.Options:
        try:
            copy_directory(self.working_dir, directory)
        except OSError as e:
            self.t.fail(f"error copying program to temp directory: {e.strerror}")
        
        options = self.options.copy()
        for opt in opts:
            opt.apply(options)
        
        return options