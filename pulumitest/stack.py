"""Stack lifecycle management for Pulumi tests.

This module provides the Stack class which manages Pulumi stack initialization,
configuration, and cleanup. It's extracted from PulumiTestProgram to enable
better separation of concerns and reusability.
"""

import logging
from pulumi import automation as auto

from .context import TestContext
from .opttest import opttest


class Stack:
    """Manages Pulumi stack lifecycle.

    Handles stack creation, initialization, and cleanup. Separates stack
    management from test orchestration for better modularity.

    Example:
        context = PyTestContext(request)
        options = opttest.default_options()
        stack = Stack(context, "my-program", options)

        # Use stack
        result = stack.current_stack.up()

        # Cleanup happens via context finalizer

    Attributes:
        context: Test context for cleanup and logging
        working_dir: Directory containing Pulumi program
        options: Test options
        current_stack: Pulumi stack instance
        local_workspace: Pulumi workspace instance
        logger: Logger for this stack
    """

    context: TestContext
    working_dir: str
    options: opttest.Options
    current_stack: auto.Stack | None
    local_workspace: auto.LocalWorkspace
    logger: logging.Logger

    defaultStackName = "test"

    def __init__(
        self,
        context: TestContext,
        working_dir: str,
        options: opttest.Options
    ):
        """Initialize stack.

        Creates a Pulumi workspace and stack, then registers cleanup
        with the test context.

        Args:
            context: Test context for cleanup and logging
            working_dir: Directory containing Pulumi program
            options: Test options

        Raises:
            Exception: If stack initialization fails
        """
        self.context = context
        self.working_dir = working_dir
        self.options = options
        self.logger = context.get_logger()

        # Initialize stack
        self._init_stack()

    def _init_stack(self) -> None:
        """Initialize Pulumi workspace and stack.

        Creates local workspace, runs pulumi install if needed,
        and creates or selects the stack.
        """
        self.logger.info("Creating local workspace...")
        self.local_workspace = auto.LocalWorkspace(work_dir=self.working_dir)

        # Run install unless skipped
        if not getattr(self.options, 'skip_install', False):
            self.logger.info("Running pulumi install...")
            self.local_workspace.install()

        # Create or select stack unless skipped
        if not getattr(self.options, 'skip_stack_create', False):
            # Get stack name from options or use default
            stack_name = getattr(self.options, 'stack_name', self.defaultStackName)

            self.logger.info(f"Running pulumi stack init... (stack: {stack_name})")
            self.current_stack = auto.create_or_select_stack(
                stack_name,
                work_dir=self.working_dir
            )
        else:
            self.logger.info("Skipping stack creation (skip_stack_create=True)")
            self.current_stack = None

    def destroy_and_remove(self) -> None:
        """Destroy and remove stack.

        Runs pulumi destroy with remove=True to clean up all resources
        and remove the stack.

        This is typically called automatically via context cleanup.
        """
        if self.current_stack is not None:
            self.logger.info("Running pulumi destroy and removing stack...")
            self.current_stack.destroy(remove=True)
        else:
            self.logger.info("No current stack, skipping destroy...")
