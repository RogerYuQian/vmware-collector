# -*- coding:utf-8 -*-

# pyvmomi

# vCenter6.0   
# 192.168.22.171
# administrator@vsphere.local
# 99Cloud!@#
# https://github.com/vmware/pyvmomi-community-samples/blob/836eddf1586a917710d4dcf2ab631fb6c1e45699/samples/esxi_perf_sample.py

from prettytable import PrettyTable

from pyVmomi import vim
from pyVim.connect import SmartConnectNoSSL, Disconnect

import sys
import logging
import datetime

LOG = logging.getLogger(__name__)

NEEDED_COUNTER = (
    'cpu:usage:averagej',
    'mem:consumed:average',
    # 'net:received:average',
    # 'net:transmitted:average',
    # 'disk:read:average',
    # 'disk:numberReadAveraged:average',
    # 'disk:write:average',
    # 'disk:numberWriteAveraged:average'
)

NODE1 = {
    'host': 'localhost',
    'user': 'administrator@vsphere.local',
    'pwd': '99Cloud!@#',
    'port': 8443
}

NODE2 = {
    'host': '192.168.22.171',
    'user': 'administrator@vsphere.local',
    'pwd': '99Cloud!@#',
    'port': 8443
}


class Vmware(object):

    def __init__(self):
        si = SmartConnectNoSSL(**NODE1)
        self.content = si.RetrieveContent()
        self.perfManager = self.content.perfManager

    @property
    def counter_info(self):
        _counter_info = getattr(self, '_counter_info', None)
        if not _counter_info:
            self._counter_info = self._get_counter_info()
        return self._counter_info

    def _get_counter_info(self):
        # [{id:name},]
        counter_info = {}
        for c in self.perfManager.perfCounter:
            fullname = '%s:%s:%s' % (c.groupInfo.key,
                                     c.nameInfo.key,
                                     c.rollupType)
            counter_info[c.key] = fullname
        return counter_info

    def get_all_power_on_nodes(self):
        return list(self.get_all_nodes(power_state='poweredOn'))

    def get_all_nodes(self, power_state=None):
        '''

        power_status valid value: poweredOff poweredOn
        '''
        container = self.content.rootFolder
        viewType = [vim.VirtualMachine]
        recursive = True

        container_view = self.content.viewManager.CreateContainerView(
                container, viewType, recursive)
        children = container_view.view
        for child in children:
            vm_power_state = child.summary.runtime.powerState
            LOG.info('%s power state is: %s',  child, vm_power_state)
            if (power_state and
                    vm_power_state != power_state):
                LOG.info('Skip %s state node: %s', power_state, child)
                continue
            yield child

    def get_counters(self, nodes):
        query_specs = []
        for node in nodes:
            needed_couter_ids = [_id for _id, name in self.counter_info.items()
                                 if name in NEEDED_COUNTER]
            metric_ids = [vim.PerformanceManager.MetricId(counterId=x)
                          for x in needed_couter_ids]
            query_spec = vim.PerformanceManager.QuerySpec(maxSample=1,
                                                          metricId=metric_ids,
                                                          entity=node)
            query_specs.append(query_spec)
        return self.perfManager.QueryPerf(querySpec=query_specs)


def print_result(nodes, results):
    header = ['Node']
    header.extend(NEEDED_COUNTER)

    x = PrettyTable(header)
    x.align['Node'] = 'r'
    for node, result in zip(nodes, results):
        data = [node.summary.config.name]
        for v in result.value:
            data.append(v.value[0])
        if len(data) < len(header):
            data.extend(['-'] * (len(header) - len(data)))
        x.add_row(data)
    print(x)


def timing(times=1):
    def outer(func):
        def wrapper(*args, **kwargs):
            LOG.info('Starting %s', func.func_name)
            start = datetime.datetime.now()
            for i in range(times):
                ret = func(*args, **kwargs)
            total = datetime.datetime.now() - start
            LOG.info('End %s total used %s', func.func_name, total)
            return ret
        return wrapper
    return outer


def performance():

    @timing(times=10)
    def one_by_one():
        vmware = Vmware()
        nodes = vmware.get_all_nodes()
        for node in nodes:
            vmware.get_counters([node])

    @timing(times=10)
    def many():
        vmware = Vmware()
        nodes = vmware.get_all_nodes()
        vmware.get_counters(nodes)

    one_by_one()
    many()


def get_one_by_one():
    vmware = Vmware()
    nodes = vmware.get_all_nodes()
    for node in nodes:
        results = vmware.get_counters([node])
        print_result([node], results)


def main():
    vmware = Vmware()
    nodes = vmware.get_all_power_on_nodes()
    results = vmware.get_counters(nodes)
    print_result(nodes, results)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    globals()[sys.argv[1]]()
