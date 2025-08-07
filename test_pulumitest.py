import pulumitest as pt
import unittest

class TestS3Stack(unittest.TestCase):
    def test_up(self):
        test = pt.PulumiTest(t=self, working_dir="test_stack")
        test.t.addCleanup(test.logger.info, "user defined cleanup runs first!")
        test.add_environments("aws/pulumi-ce")
        upresult = test.up()
        test.logger.info(upresult.stdout)