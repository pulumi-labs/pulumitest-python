import pulumitest as pt
import unittest

class TestS3Stack(unittest.TestCase):
    def test_all_methods(self):
        test = pt.PulumiTestProgram(t=self, working_dir="test_stack")
        test.t.addCleanup(test.logger.info, "user defined cleanup runs first!")
        test.add_environments("aws/pulumi-ce")
        test.up()
        preview_result = test.preview()
        pt.assert_preview.has_no_changes(test.t, preview_result)
        refresh_result = test.refresh()
        pt.assert_refresh.has_no_changes(test.t, refresh_result)
        