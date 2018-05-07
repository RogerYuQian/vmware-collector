import unittest

from vmware_collector.services import nova
from vmware_collector.tests import base as test_base


class NovaTestCase(test_base.BaseTestCase):

    @unittest.skip('require nova')
    def test_list_instance(self):
        novaclient = nova.get_nova_client(self.conf)
        novaclient.servers.list()
