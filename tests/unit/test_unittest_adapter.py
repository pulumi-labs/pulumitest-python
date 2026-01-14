"""Unit tests for unittest adapter.

Tests that the PulumiTestProgram adapter correctly wraps the PulumiTest core
and maintains backward compatibility with the original unittest-based API.
"""

import unittest
from unittest.mock import Mock, patch
from pathlib import Path

from pulumitest.unittest_adapter import PulumiTestProgram
from pulumitest import opttest


class TestUnittestAdapter(unittest.TestCase):
    """Tests for PulumiTestProgram adapter."""

    def test_adapter_initialization(self):
        """Test that adapter initializes correctly with unittest.TestCase."""
        test = PulumiTestProgram(
            self,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        self.assertIsNotNone(test)
        self.assertEqual(test.working_dir, "test_stack")
        self.assertIsNotNone(test.logger)
        self.assertIsNotNone(test.options)

    def test_adapter_properties(self):
        """Test that adapter properties delegate to core."""
        test = PulumiTestProgram(
            self,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        # Test property access
        self.assertEqual(test.working_dir, "test_stack")
        self.assertTrue(test.options.test_in_place)
        self.assertTrue(test.options.skip_install)
        self.assertIsNotNone(test.logger)

    def test_adapter_workspace_access(self):
        """Test accessing workspace through adapter."""
        test = PulumiTestProgram(
            self,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install()
        )

        # Should be able to access workspace
        workspace = test.local_workspace
        self.assertIsNotNone(workspace)

        # Should be able to access stack
        stack = test.current_stack
        self.assertIsNotNone(stack)

    def test_adapter_get_env_vars(self):
        """Test get_env_vars method."""
        test = PulumiTestProgram(
            self,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        env_vars = test.get_env_vars()
        self.assertIsInstance(env_vars, dict)
        self.assertIn("PULUMI_CONFIG_PASSPHRASE", env_vars)
        self.assertIn("PULUMI_BACKEND_URL", env_vars)

    def test_adapter_set_working_dir(self):
        """Test set_working_dir method."""
        test = PulumiTestProgram(
            self,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        original_dir = test.working_dir
        test.set_working_dir("new_stack")
        self.assertEqual(test.working_dir, "new_stack")

    def test_adapter_cleanup_registered(self):
        """Test that cleanup is registered with TestCase."""
        cleanup_calls = []

        class MockTestCase(unittest.TestCase):
            def __init__(self):
                super().__init__()
                self._testMethodName = "test_mock"

            def addCleanup(self, fn, *args, **kwargs):
                cleanup_calls.append(fn)

        mock_test = MockTestCase()

        test = PulumiTestProgram(
            mock_test,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        # Cleanup should have been registered
        self.assertGreater(len(cleanup_calls), 0)

    def test_adapter_legacy_methods(self):
        """Test legacy method compatibility."""
        test = PulumiTestProgram(
            self,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        # pulumi_test_init should be a no-op (already initialized)
        test.pulumi_test_init()  # Should not raise

    def test_adapter_with_custom_options(self):
        """Test adapter with custom options."""
        custom_options = opttest.default_options()
        custom_options.config_passphrase = "test-passphrase"
        custom_options.stack_name = "custom-stack"

        test = PulumiTestProgram(
            self,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create(),
            options=custom_options
        )

        self.assertEqual(test.options.config_passphrase, "test-passphrase")
        self.assertEqual(test.options.stack_name, "custom-stack")

    def test_adapter_copy_operations(self):
        """Test copy operations create new adapter instances."""
        test = PulumiTestProgram(
            self,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        # Copy to temp dir should return new PulumiTestProgram
        copied = test.copy_to_temp_dir()
        self.assertIsInstance(copied, PulumiTestProgram)
        self.assertNotEqual(copied.working_dir, test.working_dir)
        self.assertTrue("programDir_" in copied.working_dir)

    def test_adapter_maintains_api_compatibility(self):
        """Test that all expected methods exist."""
        test = PulumiTestProgram(
            self,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        # Check all public methods exist
        expected_methods = [
            'up', 'preview', 'refresh', 'destroy',
            'update_source', 'add_environments', 'get_env_vars',
            'set_working_dir', 'copy_to_temp_dir', 'copy_to',
            'destroyAndRemoveStack', 'pulumi_test_init'
        ]

        for method_name in expected_methods:
            self.assertTrue(
                hasattr(test, method_name),
                f"Adapter should have method: {method_name}"
            )

    def test_adapter_properties_exist(self):
        """Test that all expected properties exist."""
        test = PulumiTestProgram(
            self,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install()
        )

        # Check all properties exist
        expected_properties = [
            'working_dir', 'options', 'logger',
            'current_stack', 'local_workspace'
        ]

        for prop_name in expected_properties:
            self.assertTrue(
                hasattr(test, prop_name),
                f"Adapter should have property: {prop_name}"
            )

    def test_adapter_import_compatibility(self):
        """Test that adapter can be imported from original location."""
        # Test old import path still works
        from pulumitest import PulumiTestProgram as OldImport
        from pulumitest.unittest_adapter import PulumiTestProgram as NewImport

        # Should be the same class
        self.assertEqual(OldImport, NewImport)


if __name__ == '__main__':
    unittest.main()
