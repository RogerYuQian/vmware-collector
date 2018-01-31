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

from vmware_collector import utils


def now_str():
    return utils.format_date(utils.now())


class InstanceStat(object):

    @classmethod
    def from_dict(cls, uuid, properies):
        obj = cls()
        obj.uuid = uuid
        obj.cpu_util = properies.get('cpu_util', 0.0)
        obj.memory_usage = properies.get('memory_usage', 0.0)
        yield obj

    def to_metric(self):
        return {
            'cpu_util': [{
                'value': self.cpu_util,
                'timestamp': now_str()
            }],
            'memory.usage': [{
                'value': self.memory_usage,
                'timestamp': now_str()
            }]
        }


class InterfaceStat(object):

    @classmethod
    def from_dict(cls, uuid, properies):
        network_rx = properies.get('network.rx')
        network_tx = properies.get('network.tx')
        for name in network_rx:
            obj = cls()
            obj.uuid = uuid
            obj.name = name
            obj.rx = network_rx.get(name)
            obj.tx = network_tx.get(name)
            yield obj

    def to_metric(self):
        return {
            'network.incoming.bytes.rate': [{
                'value': self.rx,
                'timestamp': self.tx
            }],
            'network.outgoing.bytes.rate': [{
                'value': self.tx,
                'timestamp': self.tx
            }]
        }


class DiskStat(object):
    @classmethod
    def from_dict(cls, uuid, properties):
        disk_read = properties.get('disk.read')
        disk_write = properties.get('disk.write')
        for name in disk_read:
            obj = cls()
            obj.uuid = uuid
            obj.name = name
            obj.read = disk_read.get(name)
            obj.write = disk_write.get(name)
            yield obj

    def to_metric(self):
        return {
            'disk.device.read.bytes.rate': [{
                'value': self.read,
                'timestamp': now_str()

            }],
            'disk.device.write.bytes.rate': [{
                'value': self.write,
                'timestamp': now_str()
            }]
        }
