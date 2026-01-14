"""
Demonstration tests for drift adoption capabilities in Python pulumitest.

This test file showcases the new features added to support drift-adopter style tests:
1. update_source() - Swap program files while maintaining stack/state
2. get_env_vars() - Extract environment variables for coordination with external tools
3. Native export_stack() / import_stack() - Provider-agnostic drift creation
4. Convenience properties - Direct access to outputs, summary, change_summary
"""

from pulumitest import PulumiTestProgram, opttest
from pulumi.automation.events import OpType
import unittest
import os
from pathlib import Path


class TestDriftAdoptionFeatures(unittest.TestCase):
    """Tests demonstrating drift adoption capabilities."""

    def test_get_env_vars(self):
        """Test that get_env_vars() returns environment variables."""
        test = PulumiTestProgram(
            self,
            "test_stack",
            opttest.test_in_place(),
            opttest.skip_install(),
            opttest.skip_stack_create()
        )

        env_vars = test.get_env_vars()

        # Should return a dictionary with Pulumi env vars
        self.assertIsInstance(env_vars, dict)
        self.assertIn("PULUMI_BACKEND_URL", env_vars)
        self.assertIn("PULUMI_CONFIG_PASSPHRASE", env_vars)

        # Should return correct passphrase value
        self.assertEqual(env_vars["PULUMI_CONFIG_PASSPHRASE"], "correct horse battery staple")

    def test_update_source_preserves_stack(self):
        """Test that update_source() swaps files without affecting stack."""
        test = PulumiTestProgram(self, "test_stack")
        test.add_environments("aws/pulumi-ce")

        # Initial deployment
        test.up()

        # Get stack reference before update_source
        stack_before = test.current_stack
        working_dir_before = test.working_dir

        # Update source from the same directory (no-op for testing)
        test.update_source("test_stack")

        # Stack and working_dir should remain the same
        self.assertIs(test.current_stack, stack_before)
        self.assertEqual(test.working_dir, working_dir_before)

        # Stack should still be functional
        preview = test.preview()
        preview.has_no_changes()

    def test_convenience_properties_preview(self):
        """Test direct access to preview result properties."""
        test = PulumiTestProgram(self, "test_stack")
        test.add_environments("aws/pulumi-ce")

        # Deploy stack
        test.up()

        # Run preview and access properties directly
        preview = test.preview()

        # Test new convenience property
        change_summary = preview.change_summary
        self.assertIsInstance(change_summary, dict)

        # Should have no changes
        same_count = change_summary.get(OpType.SAME, 0)
        self.assertGreater(same_count, 0)

        # No updates should exist
        update_count = change_summary.get(OpType.UPDATE, 0)
        self.assertEqual(update_count, 0)

    def test_convenience_properties_update(self):
        """Test direct access to update result properties."""
        test = PulumiTestProgram(self, "test_stack")
        test.add_environments("aws/pulumi-ce")

        # Deploy stack and get result
        result = test.up()

        # Test new convenience properties
        outputs = result.outputs
        self.assertIsInstance(outputs, dict)
        self.assertIn("bucket_name", outputs)

        summary = result.summary
        self.assertIsNotNone(summary)

        change_summary = result.change_summary
        self.assertIsInstance(change_summary, dict)

    def test_convenience_properties_refresh(self):
        """Test direct access to refresh result properties."""
        test = PulumiTestProgram(self, "test_stack")
        test.add_environments("aws/pulumi-ce")

        # Deploy stack
        test.up()

        # Run refresh and access properties directly
        refresh = test.refresh()

        # Test new convenience properties
        summary = refresh.summary
        self.assertIsNotNone(summary)

        change_summary = refresh.change_summary
        self.assertIsInstance(change_summary, dict)

    def test_change_summary_count_op(self):
        """Test the count_op helper method on ChangeSummary."""
        from pulumitest.change_summary import ChangeSummary

        test = PulumiTestProgram(self, "test_stack")
        test.add_environments("aws/pulumi-ce")

        # Deploy stack
        test.up()

        # Run preview and test count_op helper
        preview = test.preview()
        change_summary_obj = ChangeSummary(preview.preview_result.change_summary)

        # Should have some SAME operations
        same_count = change_summary_obj.count_op(OpType.SAME)
        self.assertGreater(same_count, 0)

        # Should have no UPDATE operations
        update_count = change_summary_obj.count_op(OpType.UPDATE)
        self.assertEqual(update_count, 0)

        # Non-existent operation should return 0
        delete_count = change_summary_obj.count_op(OpType.DELETE)
        self.assertEqual(delete_count, 0)


class TestDriftCreationWorkflow(unittest.TestCase):
    """
    Tests demonstrating the full provider-agnostic drift creation workflow.

    Note: These tests require a more complex setup with original/ and drifted/
    program directories. This is a template showing how such tests would work.
    """

    def test_drift_creation_workflow_concept(self):
        """
        Conceptual test showing the drift creation workflow.

        This test demonstrates the pattern but uses the same code for both
        original and drifted versions (so no actual drift is created).

        For real drift testing, you would need:
        - original/ directory with initial program
        - drifted/ directory with modified program (e.g., added tags, changed properties)
        """
        # Step 1: Create test instance and copy to temp dir
        test = PulumiTestProgram(self, "test_stack").copy_to_temp_dir()
        test.add_environments("aws/pulumi-ce")

        # Step 2: Deploy original version
        # In real scenario: test.update_source("path/to/original")
        test.up()

        # Step 3: Export current state using native Automation API
        saved_state = test.current_stack.export_stack()
        self.assertIsNotNone(saved_state, "Should successfully export stack state")

        # Step 4: Switch to drifted version and deploy
        # In real scenario: test.update_source("path/to/drifted")
        # This would deploy infrastructure changes
        # test.up()

        # Step 5: Import original state (creates drift!)
        # This restores Pulumi's state to the original while infrastructure has changed
        test.current_stack.import_stack(saved_state)

        # Step 6: Switch back to original code
        # In real scenario: test.update_source("path/to/original")

        # Step 7: Verify drift would be detected
        # In real scenario with actual drift:
        # test.refresh()  # Capture infrastructure changes
        # preview = test.preview()
        # update_count = preview.change_summary.get(OpType.UPDATE, 0)
        # self.assertGreater(update_count, 0, "Expected drift to be detected")

        # For this demo, verify no drift exists since we didn't actually change anything
        test.refresh()
        preview = test.preview()
        update_count = preview.change_summary.get(OpType.UPDATE, 0)
        self.assertEqual(update_count, 0, "No drift expected in demo")

    def test_stack_export_import_roundtrip(self):
        """Test that export/import operations work correctly."""
        test = PulumiTestProgram(self, "test_stack")
        test.add_environments("aws/pulumi-ce")

        # Deploy stack
        test.up()

        # Export state
        saved_state = test.current_stack.export_stack()
        self.assertIsNotNone(saved_state)

        # Import the same state (no-op but validates the operation works)
        test.current_stack.import_stack(saved_state)

        # Verify stack is still functional
        preview = test.preview()
        preview.has_no_changes()

        refresh = test.refresh()
        refresh.has_no_changes()


class TestUpdateSourceBehavior(unittest.TestCase):
    """
    Tests to verify update_source() behavior in detail.

    These tests validate that update_source() correctly:
    - Copies program files
    - Preserves .pulumi/ directory
    - Preserves Pulumi.yaml files
    - Maintains stack object
    """

    def test_update_source_preserves_pulumi_directory(self):
        """Test that update_source() preserves the .pulumi/ state directory."""
        test = PulumiTestProgram(self, "test_stack")
        test.add_environments("aws/pulumi-ce")

        # Deploy to create .pulumi/ directory
        test.up()

        # Verify .pulumi/ directory exists
        pulumi_dir = Path(test.working_dir) / ".pulumi"
        self.assertTrue(pulumi_dir.exists(), ".pulumi directory should exist")

        # Get a file from .pulumi/ directory to check later
        pulumi_files_before = list(pulumi_dir.rglob("*"))
        self.assertGreater(len(pulumi_files_before), 0, "Should have files in .pulumi/")

        # Update source (using same directory for this test)
        test.update_source("test_stack")

        # Verify .pulumi/ directory still exists and has same files
        self.assertTrue(pulumi_dir.exists(), ".pulumi directory should still exist")
        pulumi_files_after = list(pulumi_dir.rglob("*"))

        # Should have same number of files in .pulumi/
        self.assertEqual(
            len(pulumi_files_before),
            len(pulumi_files_after),
            ".pulumi directory should be preserved"
        )

    def test_update_source_with_different_directory(self):
        """
        Test update_source() with a different source directory.

        This demonstrates the intended use case where you swap between
        different program versions while maintaining the same stack.
        """
        test = PulumiTestProgram(self, "test_stack").copy_to_temp_dir()
        test.add_environments("aws/pulumi-ce")

        # Initial deployment
        test.up()
        initial_outputs = test.current_stack.outputs()

        # Update source from test_stack again (simulating a code change)
        # In real scenario, this would be a different directory with modified code
        test.update_source("test_stack")

        # Stack should still exist with same state
        self.assertIsNotNone(test.current_stack)
        current_outputs = test.current_stack.outputs()

        # Outputs should match (since we didn't actually change infrastructure)
        self.assertEqual(initial_outputs, current_outputs)

        # Preview should show no changes
        preview = test.preview()
        preview.has_no_changes()


if __name__ == "__main__":
    unittest.main()
