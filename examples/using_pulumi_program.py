"""Examples of using PulumiProgram - the framework-independent API.

PulumiProgram has ZERO test framework dependencies. You can use it anywhere:
- In pytest tests (register cleanup with request.addfinalizer)
- In unittest tests (register cleanup with self.addCleanup)
- In standalone scripts
- In pulumi-service/cmd/agents tests
- Anywhere you need Pulumi Automation API

The key benefit: You control cleanup registration yourself.
"""

import pytest
import unittest
from pulumitest import PulumiProgram, opttest


# ============================================================================
# Example 1: Using in pytest (pulumi-service/cmd/agents style)
# ============================================================================

def test_with_pytest_manual_cleanup(request):
    """Use PulumiProgram in pytest with manual cleanup registration."""
    # Create program
    program = PulumiProgram("test_stack")

    # Register cleanup with pytest
    request.addfinalizer(program.cleanup)

    # Use the program
    result = program.up()
    assert "bucket_name" in result.outputs

    preview = program.preview()
    preview.has_no_changes()

    # Cleanup happens automatically via request.addfinalizer


def test_with_pytest_and_options(request):
    """Use PulumiProgram with options in pytest."""
    program = PulumiProgram(
        "test_stack",
        opttest.test_in_place(),
        opttest.skip_install()
    )
    request.addfinalizer(program.cleanup)

    program.add_environments("aws/pulumi-ce")
    program.up()

    # Test passes, cleanup registered


def test_with_pytest_factory(request):
    """Create a factory function for PulumiProgram in pytest."""

    def create_program(working_dir: str, *opts):
        """Factory that creates program with cleanup registered."""
        program = PulumiProgram(working_dir, *opts)
        request.addfinalizer(program.cleanup)
        return program

    # Use factory to create programs
    program1 = create_program("test_stack")
    program2 = create_program("another_stack", opttest.test_in_place())

    # Both have cleanup registered
    program1.up()
    program2.up()


# ============================================================================
# Example 2: Using in unittest
# ============================================================================

class TestWithUnittest(unittest.TestCase):
    """Use PulumiProgram in unittest tests."""

    def test_basic_deployment(self):
        """Basic usage with unittest."""
        program = PulumiProgram("test_stack")
        self.addCleanup(program.cleanup)

        program.up()

        preview = program.preview()
        preview.has_no_changes()

    def test_with_options(self):
        """With options in unittest."""
        program = PulumiProgram(
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install()
        )
        self.addCleanup(program.cleanup)

        program.add_environments("aws/pulumi-ce")
        result = program.up()
        self.assertIn("bucket_name", result.outputs)


# ============================================================================
# Example 3: Standalone usage (scripts, notebooks, etc.)
# ============================================================================

def standalone_deployment():
    """Use PulumiProgram in a standalone script."""
    program = PulumiProgram("test_stack")

    try:
        # Deploy
        result = program.up()
        print(f"Deployed! Outputs: {result.outputs}")

        # Preview
        preview = program.preview()
        if preview.has_changes():
            print("Warning: Stack has unexpected changes!")

        # Refresh
        refresh = program.refresh()
        if refresh.has_changes():
            print("Warning: Stack state differs from actual infrastructure!")

    finally:
        # Manual cleanup
        program.cleanup()


def standalone_with_context_manager():
    """Use with a context manager for automatic cleanup."""

    class ProgramContext:
        """Context manager wrapper for PulumiProgram."""

        def __init__(self, *args, **kwargs):
            self.program = PulumiProgram(*args, **kwargs)

        def __enter__(self):
            return self.program

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.program.cleanup()
            return False

    # Use as context manager
    with ProgramContext("test_stack") as program:
        program.up()
        # Cleanup automatic on exit


# ============================================================================
# Example 4: pulumi-service/cmd/agents integration style
# ============================================================================

def test_agents_integration_style(request):
    """Example matching pulumi-service/cmd/agents test structure.

    This shows how to integrate PulumiProgram into existing test suites
    that have their own pytest setup.
    """
    # Your existing test setup
    # ... whatever setup you already have ...

    # Create Pulumi program
    program = PulumiProgram(
        "test_stack",
        opttest.test_in_place(),  # Don't copy to temp
        opttest.skip_install()     # Already installed
    )

    # Register cleanup with pytest (works with any pytest version)
    request.addfinalizer(program.cleanup)

    # Add cloud credentials
    program.add_environments("aws/pulumi-ce")

    # Deploy infrastructure
    result = program.up()

    # Your test assertions
    outputs = result.outputs
    assert "api_endpoint" in outputs
    assert outputs["api_endpoint"].startswith("https://")

    # Do your agent testing
    # ... test your agents against the deployed infrastructure ...

    # Cleanup happens automatically


# ============================================================================
# Example 5: Advanced usage - Copy and update source
# ============================================================================

def test_drift_detection(request):
    """Advanced example showing drift detection workflow."""
    # Create original program
    original = PulumiProgram("test_stack_original")
    request.addfinalizer(original.cleanup)

    # Deploy original
    original.up()

    # Export state
    state = original.current_stack.export_stack()

    # Create drifted program
    drifted = PulumiProgram("test_stack_drifted")
    request.addfinalizer(drifted.cleanup)

    # Import state into drifted stack
    drifted.current_stack.import_stack(state)

    # Deploy drifted version
    drifted.up()

    # Now check original for drift
    original.update_source("test_stack_original")
    refresh = original.refresh()

    # Assert drift detected
    assert refresh.has_changes(), "Expected drift to be detected"


# ============================================================================
# Example 6: Multiple stacks in one test
# ============================================================================

def test_multiple_stacks(request):
    """Test with multiple Pulumi programs."""
    # Create frontend stack
    frontend = PulumiProgram("frontend_stack")
    request.addfinalizer(frontend.cleanup)

    # Create backend stack
    backend = PulumiProgram("backend_stack")
    request.addfinalizer(backend.cleanup)

    # Deploy both
    backend_result = backend.up()
    frontend_result = frontend.up()

    # Test integration between stacks
    backend_url = backend_result.outputs["api_url"]
    frontend_api = frontend_result.outputs["configured_api"]

    assert frontend_api == backend_url


# ============================================================================
# Example 7: Using with custom logger
# ============================================================================

def test_with_custom_logger(request):
    """Use PulumiProgram with custom logger."""
    import logging

    # Create custom logger
    logger = logging.getLogger("my_custom_logger")
    logger.setLevel(logging.INFO)

    # Create program with custom logger
    program = PulumiProgram(
        "test_stack",
        logger=logger
    )
    request.addfinalizer(program.cleanup)

    # All log messages go to custom logger
    program.up()


# ============================================================================
# Example 8: Getting environment variables for external tools
# ============================================================================

def test_with_external_tools(request):
    """Use PulumiProgram with external Pulumi CLI tools."""
    import subprocess

    program = PulumiProgram("test_stack")
    request.addfinalizer(program.cleanup)

    # Deploy
    program.up()

    # Get env vars for external commands
    env_vars = program.get_env_vars()

    # Run external Pulumi command with same config
    result = subprocess.run(
        ["pulumi", "stack", "output"],
        cwd=program.working_dir,
        env={**subprocess.os.environ, **env_vars},
        capture_output=True,
        text=True
    )

    assert result.returncode == 0


if __name__ == "__main__":
    # Run standalone example
    print("Running standalone deployment example...")
    standalone_deployment()
