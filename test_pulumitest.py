from pulumitest import PulumiTestProgram, opttest, PreviewResult, RefreshResult, UpdateResult
import unittest

class TestS3Stack(unittest.TestCase):
    def test_all_methods(self):
        test_program = PulumiTestProgram(self, "test_stack")
        self.addCleanup(test_program.logger.info, "user defined cleanup runs first!")
        test_program.add_environments("aws/pulumi-ce")
        test_program.up()
        preview_result = test_program.preview()
        preview_result.has_no_changes()
        refresh_result = test_program.refresh()
        refresh_result.has_no_changes()
    
    def test_copy_option(self):
        test_program = PulumiTestProgram(self, "test_stack", opttest.test_in_place(), opttest.skip_install(), opttest.skip_stack_create())
        test_program.logger.info(f"test.working_dir: {test_program.working_dir}")
        self.assertEqual(test_program.working_dir, "test_stack")
        moved_test = test_program.copy_to_temp_dir(opttest.stack_name())
        moved_test.logger.info(f"moved_test.working_dir: {moved_test.working_dir}")
        moved_test.add_environments("aws/pulumi-ce")
        moved_test.up()
        preview_result = moved_test.preview()
        preview_result.has_no_changes()