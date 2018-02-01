'''
{8a52e718-d3a5-4d8e-9e13-6ce7a2a5e3d3: {
    'cpu_util': 0.05,
    'disk.read': {naa.61866da050c6c6002078db7b15bf3e71: 0.0},
    'disk.write': {naa.61866da050c6c6002078db7b15bf3e71: 0.0},
    'network.rx': {4000: 0.0},
    'network.tx': {4000: 0.0},
    'memory_usage': 75776.0},
 b6275f6e-f8f0-4d31-bbbb-32ed1c577ab4: {
    'cpu_util': 0.02,
    'disk.read': {naa.61866da050c6c6002078db7b15bf3e71: 0.0},
    'disk.write': {naa.61866da050c6c6002078db7b15bf3e71: 0.0},
    'network.rx': {4000: 0.0},
    'network.tx': {4000: 0.0},
    'memory_usage': 74168.0}}
'''
import logging

from vmware_collector import utils
from vmware_collector import gnocchi

LOG = logging.getLogger(__name__)


def now_str():
    return utils.format_date(utils.now())


class BaseStat(object):
    def __init__(self, conf, uuid):
        self.conf = conf
        self.uuid = uuid
        self.gnocchi_helper = gnocchi.get_gnocchi_helper(conf)

    def __repr__(self):
        return '<%s uuid:%s resource: %s>' % (self.__class__.__name__,
                                              self.uuid, self.resource['id'])


class InstanceStat(BaseStat):
    resource_type = 'instance'

    @classmethod
    def from_dict(cls, conf, uuid, properies):
        obj = cls(conf, uuid)
        obj.cpu_util = properies.get('cpu_util', 0.0)
        obj.memory_usage = properies.get('memory_usage', 0.0)
        obj.resource = obj.gnocchi_helper.get_instance_resource(uuid)
        yield obj

    def to_metric(self):
        return {
            self.resource['id']: {
                'cpu_util': [{
                    'value': self.cpu_util,
                    'timestamp': now_str()
                }],
                'memory.usage': [{
                    'value': self.memory_usage,
                    'timestamp': now_str()
                }]
            }
        }


class InterfaceStat(BaseStat):
    resource_type = 'instance_network_interface'

    @classmethod
    def from_dict(cls, conf, uuid, properies):
        network_rx = properies.get('network.rx')
        network_tx = properies.get('network.tx')
        for name in network_rx:
            obj = cls(conf, uuid)
            obj.name = name
            obj.rx = network_rx.get(name)
            obj.tx = network_tx.get(name)
            gh = obj.gnocchi_helper
            obj.resource = gh.get_instance_network_resource(uuid, name)
            yield obj

    def to_metric(self):
        return {
            self.resource['id']: {
                'network.incoming.bytes.rate': [{
                    'value': self.rx,
                    'timestamp': now_str()
                }],
                'network.outgoing.bytes.rate': [{
                    'value': self.tx,
                    'timestamp': now_str()
                }]
            }
        }


class DiskStat(BaseStat):
    resource_type = 'instance_disk'

    @classmethod
    def from_dict(cls, conf, uuid, properties):
        disk_read = properties.get('disk.read')
        disk_write = properties.get('disk.write')
        for name in disk_read:
            obj = cls(conf, uuid)
            obj.name = name
            obj.read = disk_read.get(name)
            obj.write = disk_write.get(name)
            obj.resource = obj.gnocchi_helper.get_instance_disk_resource(
                uuid, name)
            yield obj

    def to_metric(self):
        return {
            self.resource['id']: {
                'disk.device.read.bytes.rate': [{
                    'value': self.read,
                    'timestamp': now_str()
                }],
                'disk.device.write.bytes.rate': [{
                    'value': self.write,
                    'timestamp': now_str()
                }]
            }
        }


STAT_CLASS = [InstanceStat, InterfaceStat, DiskStat]


def factory(conf, uuid, properties):
    for cls in STAT_CLASS:
        try:
            for stat in cls.from_dict(conf, uuid, properties):
                yield stat
        except Exception:
            LOG.exception('Failed to handle %s %s %s', cls, uuid, properties)
