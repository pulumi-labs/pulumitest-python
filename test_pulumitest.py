import pulumitest as pt
import unittest
# User defined test class, inherits from PulumiTest
# 
# class TestS3Stack(pt.PulumiTest):
#     def setUp(self):
#         super().setUp(working_dir="test_stack")
#         self.add_environments("aws/pulumi-ce")

#     def test_up(self):
#         upresult = self.up()
#         self.logger.info(upresult.stdout)

class TestS3Stack(unittest.TestCase):
    def test_up(self):
        test = pt.PulumiTest(t=self, working_dir="test_stack")
        test.add_environments("aws/pulumi-ce")
        upresult = test.up()
        test.logger.info(upresult.stdout)