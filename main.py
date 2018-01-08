# -*- coding:utf-8 -*-

# pyvmomi

# vCenter6.0   
# 192.168.22.171
# administrator@vsphere.local
# 99Cloud!@#
# https://github.com/vmware/pyvmomi-community-samples/blob/836eddf1586a917710d4dcf2ab631fb6c1e45699/samples/esxi_perf_sample.py

from prettytable import PrettyTable
from multiprocessing.pool import ThreadPool

from pyVmomi import vim
from pyVim.connect import SmartConnectNoSSL, Disconnect

import sys
import logging
import datetime

LOG = logging.getLogger(__name__)

NEEDED_COUNTER = (
    'cpu:usage:average',
    # 'mem:consumed:average',
    'mem:usage:average',
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
    'port': 443
}


class Vmware(object):

    def __init__(self):
        si = SmartConnectNoSSL(**NODE2)
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
            if (power_state and
                    vm_power_state != power_state):
                LOG.debug('Skip %s state node: %s', vm_power_state, child)
                continue
            yield child

    def get_counters(self, nodes):
        '''
        {
            "node_name": {
                "key1": "value1",
                "key2": "value2"
            },
        }
        '''
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
        results = self.perfManager.QueryPerf(querySpec=query_specs)
        ret = {}
        for node, items in zip(nodes, results):
            node_uuid = node.summary.config.instanceUuid
            ret[node_uuid] = {}
            for item_name, item in zip(NEEDED_COUNTER, items.value):
                ret[node_uuid][item_name] = item.value[0]
        LOG.debug('Get: %s', ret)
        return ret


def print_result(nodes, results):
    header = ['Node']
    header.extend(NEEDED_COUNTER)

    x = PrettyTable(header)
    x.align['Node'] = 'r'

    try:
        for node in nodes:
            node_uuid = node.summary.config.instanceUuid
            data = [node.summary.config.name]
            items = results.get(node_uuid)
            if not items:
                LOG.warning('Unable get instance counters for %s', node)
                continue
            for counter in NEEDED_COUNTER:
                data.append(items.get(counter, '-'))
            x.add_row(data)
    except Exception:
        LOG.exception('')
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

    # Get basic information

    def get_info():

        vmware = Vmware()
        nodes = list(vmware.get_all_nodes())
        up_nodes = list(vmware.get_all_power_on_nodes())
        LOG.info('Get %d nodes: %s', len(nodes), nodes)
        LOG.info('Get %d up nodes: %s', len(up_nodes), up_nodes)

    @timing(times=1)
    def get_vmware_and_nodes():
        vmware = Vmware()
        # nodes = vmware.get_all_power_on_nodes()
        nodes = vmware.get_all_nodes()
        return vmware, nodes

    @timing(times=1)
    def one_by_one():
        vmware, nodes = get_vmware_and_nodes()

        @timing(times=1)
        def inner():
            for node in nodes:
                vmware.get_counters([node])
        inner()

    @timing(times=1)
    def many():
        vmware, nodes = get_vmware_and_nodes()

        @timing(times=1)
        def inner():
            vmware.get_counters(nodes)
        inner()

    @timing(times=1)
    def run_concurrency():
        vmware, nodes = get_vmware_and_nodes()
        pool = ThreadPool(3)

        @timing(times=1)
        def inner():
            returns = []
            for sub_nodes in group(nodes, 4):
                returns.append(pool.apply_async(vmware.get_counters,
                                                (sub_nodes,)))
            for ret in returns:
                ret.get(0xff)
                # results.update(ret.get(0xff))
        inner()

    get_info()

    run_concurrency()
    one_by_one()
    many()


def get_one_by_one():
    vmware = Vmware()
    nodes = vmware.get_all_power_on_nodes()
    for node in nodes:
        results = vmware.get_counters([node])
        print_result([node], results)


def group(eles, count):
    itr = iter(eles)
    while True:
        ret = []
        try:
            for i in range(count):
                ret.append(itr.next())
            yield ret
        except StopIteration:
            if ret:
                yield ret
            raise StopIteration


def run_multi_process():
    pool = ThreadPool(10)
    vmware = Vmware()
    nodes = vmware.get_all_power_on_nodes()
    returns = []

    for sub_nodes in group(nodes, 1):
        returns.append(pool.apply_async(vmware.get_counters, (sub_nodes,)))
    results = {}
    for ret in returns:
        results.update(ret.get(0xff))
    print_result(nodes, results)


def main():
    vmware = Vmware()
    nodes = vmware.get_all_power_on_nodes()
    results = vmware.get_counters(nodes)
    print_result(nodes, results)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        func = "performance"
    else:
        func = sys.argv[1]
    if func == 'performance':
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.DEBUG)
    globals()[func]()
