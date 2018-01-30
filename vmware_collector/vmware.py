import logging

from pyVmomi import vim
from pyVim.connect import SmartConnectNoSSL, Disconnect

from vmware_collector import utils

LOG = logging.getLogger(__name__)

NEEDED_COUNTER = (
    'cpu:usage:average',
    # 'mem:consumed:average',
    'mem:usage:average',
    'net:received:average',
    'net:transmitted:average',
    # 'disk:read:average',
    # 'disk:numberReadAveraged:average',
    # 'disk:write:average',
    # 'disk:numberWriteAveraged:average'
)


class InstanceStat(object):
    def __init__(self, uuid, cpu=None, ram=None):
        # TODO(jeffrey4l): use a real uuid
        self.uuid = '67d9d526-4dee-4a15-93ba-679b2b1f2ff5'
        self.cpu = cpu
        self.ram = ram
        self.rx = 0
        self.tx = 0
        self.create_at = utils.now()

    def __repr__(self):
        return '<InstanceStat:%s cpu:%s ram:%s>' % (self.uuid, self.cpu,
                                                    self.ram)

    def to_measures(self):
        measures = {
            'cpu_util': [{
                'timestamp': utils.format_date(self.create_at),
                'value': self.cpu
            }],
            'memory.usage': [{
                'timestamp': utils.format_date(self.create_at),
                'value': self.ram
            }],
            'network.incoming.bytes': [{
                'timestamp': utils.format_date(self.create_at),
                'value': self.rx,
            }],
            'network.outgoing.bytes': [{
                'timestamp': utils.format_date(self.create_at),
                'value': self.tx,
            }]
        }
        LOG.debug('Get measures for %s: %s', self.uuid, measures)
        return measures


class Vmware(object):
    def __init__(self, conf):
        self.conf = conf
        vmware_conf = conf.vmware
        self.si = SmartConnectNoSSL(
            host=vmware_conf.host,
            user=vmware_conf.username,
            pwd=vmware_conf.password,
            port=vmware_conf.port)
        self.content = self.si.RetrieveContent()
        self.perfManager = self.content.perfManager

    def close(self):
        Disconnect(self.si)

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
            fullname = '%s:%s:%s' % (c.groupInfo.key, c.nameInfo.key,
                                     c.rollupType)
            counter_info[c.key] = fullname
        return counter_info

    def get_all_power_on_nodes(self):
        return list(self.get_all_nodes(power_state='poweredOn'))

    def get_nodes_by_name(self, names):
        container = self.content.rootFolder
        viewType = [vim.VirtualMachine]
        recursive = True

        container_view = self.content.viewManager.CreateContainerView(
            container, viewType, recursive)
        children = container_view.view
        for child in children:
            name = child.config.name
            # vm_power_state = child.summary.runtime.powerState
            if name not in names:
                continue
            yield child

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
            if (power_state and vm_power_state != power_state):
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
            needed_couter_ids = [
                _id for _id, name in self.counter_info.items()
                if name in NEEDED_COUNTER
            ]
            metric_ids = [
                vim.PerformanceManager.MetricId(counterId=x)
                for x in needed_couter_ids
            ]
            query_spec = vim.PerformanceManager.QuerySpec(
                maxSample=1, metricId=metric_ids, entity=node)
            query_specs.append(query_spec)
        results = self.perfManager.QueryPerf(querySpec=query_specs)
        ret = []
        for node, items in zip(nodes, results):
            node_uuid = node.summary.config.instanceUuid
            instance_stat = InstanceStat(node_uuid)
            for item_name, item in zip(NEEDED_COUNTER, items.value):
                if item_name == 'cpu:usage:average':
                    instance_stat.cpu = item.value[0]
                elif item_name == 'mem:usage:average':
                    instance_stat.ram = item.value[0]
                elif item_name == 'net:received:average':
                    instance_stat.rx = item.value[0]
                elif item_name == 'net:transmitted:average':
                    instance_stat.tx = item.value[0]
            ret.append(instance_stat)
        LOG.info('Get: %s', ret)
        return ret
