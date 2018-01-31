# -*- coding:utf-8 -*-
import unittest

from vmware_collector import vmware
from vmware_collector.tests import base as test_base


class VmwareTestCase(test_base.BaseTestCase):

    @unittest.skip('need a real vmware')
    def test_get_nodes_by_name(self):

        api = vmware.Vmware()
        nodes = api.get_nodes_by_name(['a48cb02f-53de-4ef6-9e2e-3aa817e93a35'])
        print([node.config.name for node in nodes])


class VmwareTestGet(test_base.BaseTestCase):

    def test(self):
        api = vmware.Vmware(self.conf)
        nodes = api.get_all_power_on_nodes()
        nodes = list(nodes)
        new_groups = []
        for node in nodes:
            if node.summary.config.name.startswith('animbus'):
                new_groups.append(node)
        stat = api.get_counters(new_groups)
        print(stat)
