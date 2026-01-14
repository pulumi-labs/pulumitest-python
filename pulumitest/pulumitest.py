"""Legacy module for backward compatibility.

This module re-exports PulumiTestProgram from unittest_adapter to maintain
backward compatibility with existing imports.

The original unittest-based implementation has been replaced with an adapter
that wraps the pytest-native core, but the API remains identical.

Usage (unchanged from before):
    from pulumitest import PulumiTestProgram

    class TestStack(unittest.TestCase):
        def test_deployment(self):
            test = PulumiTestProgram(self, "test_stack")
            test.up()
"""

# Re-export from adapter for backward compatibility
from .unittest_adapter import PulumiTestProgram

__all__ = ["PulumiTestProgram"]
