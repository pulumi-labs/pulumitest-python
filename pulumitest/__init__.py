"""Pulumitest - Testing framework for Pulumi.

This package provides both pytest-native and unittest-compatible APIs for
testing Pulumi infrastructure as code.

Pytest API (recommended):
    Use pytest fixtures for clean, native pytest integration:

    @pytest.mark.pulumi_program_dir("test_stack")
    def test_deployment(pulumi_stack):
        outputs = pulumi_stack.current_stack.outputs()
        assert "bucket_name" in outputs

Unittest API (backward compatible):
    Use PulumiTestProgram for existing unittest-based tests:

    class TestStack(unittest.TestCase):
        def test_deployment(self):
            test = PulumiTestProgram(self, "test_stack")
            test.up()

Both APIs share the same core implementation and support the same features.
"""

# Backward-compatible unittest API
from .pulumitest import PulumiTestProgram

# Pytest-native API
from .core import PulumiTest
from .pytest_context import PyTestContext
from .unittest_context import UnittestContext
from .context import TestContext

# Shared components
from .opttest import opttest
from .result import Result, PreviewResult, RefreshResult, UpdateResult

# Pytest fixtures are automatically available via plugin registration
# Import pytest_plugin to access fixtures: pulumi_test, pulumi_stack, etc.

__all__ = [
    # Unittest API (backward compatible)
    "PulumiTestProgram",

    # Pytest-native API
    "PulumiTest",
    "PyTestContext",
    "UnittestContext",
    "TestContext",

    # Shared
    "opttest",
    "Result",
    "PreviewResult",
    "RefreshResult",
    "UpdateResult",
]