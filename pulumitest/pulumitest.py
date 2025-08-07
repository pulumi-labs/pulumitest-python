import sys
from pulumi import automation as auto
import subprocess
import unittest
import logging

class PulumiTestAlt(unittest.TestCase):
    current_stack: auto.Stack
    working_dir: str
    logger: logging.Logger
    stream_handler: logging.StreamHandler

    defaultStackName = "test"
    
    def setUp(self, working_dir: str):
        self.stream_handler = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(self.stream_handler)
        self.logger.info("Running pulumi install...")
        self.pulumi_install(working_dir)
        self.logger.info("Running pulumi stack init...")
        self.current_stack = auto.create_or_select_stack(self.defaultStackName, work_dir=working_dir)

    def tearDown(self):
        self.logger.info("Running pulumi down --remove...")
        self.current_stack.destroy(remove=True)
        self.logger.removeHandler(self.stream_handler)

    def __init__(self, test_method: str):
        super().__init__(test_method)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
    def pulumi_install(self, working_dir: str):
        try:
            subprocess.run(args=["pulumi", "install"], cwd=working_dir, check=True, capture_output=True)
        except subprocess.CalledProcessError as err:
            self.fail(f"failed to install packages and plugins: {err.stderr}\n{err.stdout}")

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

class PulumiTest():
    current_stack: auto.Stack
    working_dir: str
    logger: logging.Logger
    stream_handler: logging.StreamHandler

    defaultStackName = "test"        

    def tearDown(self):
        self.logger.info("Running pulumi down --remove...")
        self.current_stack.destroy(remove=True)
        self.logger.removeHandler(self.stream_handler)

    def __init__(self, t: unittest.TestCase, working_dir: str):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.stream_handler = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(self.stream_handler)
        self.logger.info("Running pulumi install...")
        self.pulumi_install(working_dir)
        self.logger.info("Running pulumi stack init...")
        self.current_stack = auto.create_or_select_stack(self.defaultStackName, work_dir=working_dir)
        t.tearDown = self.tearDown

    def pulumi_install(self, working_dir: str):
        try:
            subprocess.run(args=["pulumi", "install"], cwd=working_dir, check=True, capture_output=True)
        except subprocess.CalledProcessError as err:
            self.fail(f"failed to install packages and plugins: {err.stderr}\n{err.stdout}")

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

# TODO
# create test options and default options
# copy to temp dir function
# create pulumi install function
# initialize Stack with auto
# create automatic teardown