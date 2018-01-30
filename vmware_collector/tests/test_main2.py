import unittest

from vmware_collector.tests import base as test_base
from vmware_collector import main2


class ManagerTest(test_base.BaseTestCase):

    # @unittest.skip('')
    def test_run(self):
        mgr = main2.Manager(self.conf)
        mgr.run()
