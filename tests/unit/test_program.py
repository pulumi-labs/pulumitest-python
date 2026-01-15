"""Unit tests for PulumiProgram - framework-independent API."""

import unittest
from pathlib import Path

from pulumitest.program import PulumiProgram
from pulumitest import opttest


class TestPulumiProgram(unittest.TestCase):
    """Tests for framework-independent PulumiProgram."""

    def test_program_initialization(self):
        """Test that PulumiProgram initializes without test framework."""
        program = PulumiProgram(
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        self.assertEqual(program.working_dir, "test_stack")
        self.assertIsNotNone(program.logger)
        self.assertIsNotNone(program.options)
        self.assertTrue(program.options.test_in_place)

    def test_program_with_custom_options(self):
        """Test PulumiProgram with custom options."""
        custom_options = opttest.default_options()
        custom_options.config_passphrase = "test-secret"
        custom_options.stack_name = "custom"

        program = PulumiProgram(
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create(),
            options=custom_options
        )

        self.assertEqual(program.options.config_passphrase, "test-secret")
        self.assertEqual(program.options.stack_name, "custom")

    def test_program_cleanup_callable(self):
        """Test that cleanup method exists and is callable."""
        program = PulumiProgram(
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        # Cleanup should be callable
        self.assertTrue(callable(program.cleanup))

        # Should not raise when called
        program.cleanup()

    def test_program_get_env_vars(self):
        """Test get_env_vars returns environment variables."""
        program = PulumiProgram(
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        env_vars = program.get_env_vars()

        self.assertIsInstance(env_vars, dict)
        self.assertIn("PULUMI_CONFIG_PASSPHRASE", env_vars)
        self.assertIn("PULUMI_BACKEND_URL", env_vars)

    def test_program_set_working_dir(self):
        """Test set_working_dir method."""
        program = PulumiProgram(
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        original_dir = program.working_dir
        program.set_working_dir("new_dir")
        self.assertEqual(program.working_dir, "new_dir")
        self.assertNotEqual(program.working_dir, original_dir)

    def test_program_workspace_access(self):
        """Test accessing workspace."""
        program = PulumiProgram(
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install()
        )

        # Should have workspace
        self.assertIsNotNone(program.local_workspace)

        # Should have stack
        self.assertIsNotNone(program.current_stack)
        self.assertEqual(program.current_stack.name, "test")

        # Cleanup
        program.cleanup()

    def test_program_copy_operations(self):
        """Test copy operations."""
        program = PulumiProgram(
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        # Copy to temp dir
        copied = program.copy_to_temp_dir()

        self.assertIsInstance(copied, PulumiProgram)
        self.assertNotEqual(copied.working_dir, program.working_dir)
        self.assertTrue("programDir_" in copied.working_dir)

        # Cleanup both
        program.cleanup()
        copied.cleanup()

    def test_program_no_test_framework_dependency(self):
        """Test that PulumiProgram has no test framework dependencies."""
        # Should be able to create without any test framework
        program = PulumiProgram(
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        # Should not have any test framework attributes
        self.assertFalse(hasattr(program, 't'))  # No unittest.TestCase
        self.assertFalse(hasattr(program, 'context'))  # No TestContext
        self.assertFalse(hasattr(program, '_request'))  # No pytest request

        program.cleanup()

    def test_program_all_methods_exist(self):
        """Test that all expected methods exist."""
        program = PulumiProgram(
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        expected_methods = [
            'up', 'preview', 'refresh', 'destroy',
            'update_source', 'add_environments', 'get_env_vars',
            'set_working_dir', 'copy_to_temp_dir', 'copy_to',
            'cleanup'
        ]

        for method_name in expected_methods:
            self.assertTrue(
                hasattr(program, method_name),
                f"PulumiProgram should have method: {method_name}"
            )
            self.assertTrue(
                callable(getattr(program, method_name)),
                f"PulumiProgram.{method_name} should be callable"
            )

        program.cleanup()

    def test_program_properties_exist(self):
        """Test that all expected properties exist."""
        program = PulumiProgram(
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        expected_properties = [
            'working_dir', 'options', 'logger',
            'current_stack', 'local_workspace'
        ]

        for prop_name in expected_properties:
            self.assertTrue(
                hasattr(program, prop_name),
                f"PulumiProgram should have property: {prop_name}"
            )

        program.cleanup()

    def test_program_import_from_main_package(self):
        """Test that PulumiProgram can be imported from main package."""
        from pulumitest import PulumiProgram as ImportedProgram

        # Should be the same class
        self.assertEqual(PulumiProgram, ImportedProgram)

    def test_program_with_custom_logger(self):
        """Test PulumiProgram with custom logger."""
        import logging

        custom_logger = logging.getLogger("test_custom")
        custom_logger.setLevel(logging.DEBUG)

        program = PulumiProgram(
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create(),
            logger=custom_logger
        )

        # Should use custom logger
        self.assertEqual(program.logger, custom_logger)

        program.cleanup()


class TestPulumiProgramIntegration(unittest.TestCase):
    """Integration tests for PulumiProgram with actual Pulumi operations."""

    def test_program_can_be_used_in_unittest(self):
        """Test that PulumiProgram works in unittest with addCleanup."""
        program = PulumiProgram(
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        # Register cleanup with unittest
        self.addCleanup(program.cleanup)

        # Should work without errors
        self.assertIsNotNone(program.working_dir)


if __name__ == '__main__':
    unittest.main()
