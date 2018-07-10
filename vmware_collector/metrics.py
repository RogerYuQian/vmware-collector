# coding: utf-8

import re

from oslo_log import log
from oslo_utils import units

from vmware_collector.common import utils
from vmware_collector.services import neutron


LOG = log.getLogger(__name__)

VC_AVERAGE_MEMORY_CONSUMED_CNTR = 'mem:consumed:average'
VC_AVERAGE_CPU_CONSUMED_CNTR = 'cpu:usage:average'
VC_NETWORK_RX_COUNTER = 'net:received:average'
VC_NETWORK_TX_COUNTER = 'net:transmitted:average'
VC_VIRTUAL_DISK_READ_RATE_CNTR = "virtualDisk:read:average"
VC_VIRTUAL_DISK_WRITE_RATE_CNTR = "virtualDisk:write:average"
VC_VIRTUAL_DISK_READ_IOPS_CNTR = "virtualDisk:numberReadAveraged:average"
VC_VIRTUAL_DISK_WRITE_IOPS_CNTR = "virtualDisk:numberWriteAveraged:average"

translation_mapping = {'root': ['硬盘 1', 'Hard disk 1'],
                       'cd_dvd': ['CD/DVD 驱动器', 'CD/DVD drive']}


class BaseMetric(object):
    counter_name = None
    instance = ''
    gnocchi_resource_type = None

    def __init__(self, conf, inspector):
        self.conf = conf
        self.inspector = inspector
        self.counter_id = inspector.get_perf_counter_id(self.counter_name)

    def get_metric(self):
        session = self.inspector._api_session
        client_factory = session.vim.client.factory

        metric_id = client_factory.create('ns0:PerfMetricId')
        metric_id.counterId = self.counter_id
        metric_id.instance = self.instance
        return metric_id

    def handle_result(self, entity_metric):
        stat = {}
        for metric_series in entity_metric.value:
            if metric_series.id.counterId != self.counter_id:
                continue
            # Take the average of all samples to improve the accuracy
            # of the stat value and ignore -1 (bug 1639114)
            filtered = [i for i in metric_series.value if i != -1]
            if len(filtered) != 0:
                stat_value = float(sum(filtered)) / len(filtered)
            else:
                stat_value = 0
            device_id = metric_series.id.instance
            stat[device_id] = stat_value
        return stat


class CPUMetric(BaseMetric):
    counter_name = VC_AVERAGE_CPU_CONSUMED_CNTR
    gnocchi_resource_type = 'instance'
    gnocchi_metric_name = 'cpu_util'

    def handle_result(self, entity_metric):
        stat = super(CPUMetric, self).handle_result(entity_metric)
        cpu_util = stat.pop(None, 0)
        yield None, float(cpu_util)/100


class RAMMetric(BaseMetric):
    counter_name = VC_AVERAGE_MEMORY_CONSUMED_CNTR
    gnocchi_resource_type = 'instance'
    gnocchi_metric_name = 'memory_usage'

    def handle_result(self, entity_metric):
        stat = super(RAMMetric, self).handle_result(entity_metric)
        ram = stat.pop(None, 0)
        yield None, ram


class NetworkTXMetric(BaseMetric):
    counter_name = VC_NETWORK_TX_COUNTER
    gnocchi_resource_type = 'instance_network_interface'
    instance = '*'
    gnocchi_metric_name = 'network.outcoming.bytes.rate'

    def handle_result(self, entity_metric):
        stat = super(NetworkTXMetric, self).handle_result(entity_metric)
        # For some device counters, in addition to the per device value
        # the Performance manager also returns the aggregated value.
        # Just to be consistent, deleting the aggregated value if present.
        stat.pop(None, None)
        # The sample for this map is: {4000: 0.0, vmnic5: 0.0, vmnic4: 0.0,
        #               vmnic3: 0.0, vmnic2: 0.0, vmnic1: 0.0, vmnic0: 0.0}
        # "4000" is the virtual nic which we need.
        # And these "vmnic*" are phynical nics in the host, so we remove it
        stat = {k: v for (k, v) in stat.items() if not k.startswith('vmnic')}
        devices = self.inspector.get_hardware_device(entity_metric)
        stat = _change_key2port(self.conf, stat, devices)
        for port_id, value in stat.items():
            yield port_id, value * units.Ki


class NetworkRXMetric(BaseMetric):
    counter_name = VC_NETWORK_RX_COUNTER
    gnocchi_resource_type = 'instance_network_interface'
    instance = '*'
    gnocchi_metric_name = 'network.incoming.bytes.rate'

    def handle_result(self, entity_metric):
        stat = super(NetworkRXMetric, self).handle_result(entity_metric)
        # For some device counters, in addition to the per device value
        # the Performance manager also returns the aggregated value.
        # Just to be consistent, deleting the aggregated value if present.
        stat.pop(None, None)
        # The sample for this map is: {4000: 0.0, vmnic5: 0.0, vmnic4: 0.0,
        #               vmnic3: 0.0, vmnic2: 0.0, vmnic1: 0.0, vmnic0: 0.0}
        # "4000" is the virtual nic which we need.
        # And these "vmnic*" are phynical nics in the host, so we remove it
        stat = {k: v for (k, v) in stat.items()
                if not k.startswith('vmnic')}
        devices = self.inspector.get_hardware_device(entity_metric)
        stat = _change_key2port(self.conf, stat, devices)
        for port_id, value in stat.items():
            yield port_id, value * units.Ki


class DiskReadMetric(BaseMetric):
    counter_name = VC_VIRTUAL_DISK_READ_RATE_CNTR
    instance = '*'
    gnocchi_resource_type = 'instance_disk'
    gnocchi_metric_name = 'disk.device.read.bytes.rate'

    def handle_result(self, entity_metric):
        stat = super(DiskReadMetric, self).handle_result(entity_metric)
        # For some device counters, in addition to the per device value
        # the Performance manager also returns the aggregated value.
        # Just to be consistent, deleting the aggregated value if present.
        stat.pop(None, None)
        devices = self.inspector.get_hardware_device(entity_metric)
        stat = _change_dev2vol(self.conf, stat, devices)
        # Stats provided from vSphere are in KB/s, converting it to B/s.
        for key in stat:
            value = stat.get(key, 0) * units.Ki
            yield key, value


class DiskWriteMetric(BaseMetric):
    counter_name = VC_VIRTUAL_DISK_WRITE_RATE_CNTR
    instance = '*'
    gnocchi_resource_type = 'instance_disk'
    gnocchi_metric_name = 'disk.device.write.bytes.rate'

    def handle_result(self, entity_metric):
        stat = super(DiskWriteMetric, self).handle_result(entity_metric)
        # For some device counters, in addition to the per device value
        # the Performance manager also returns the aggregated value.
        # Just to be consistent, deleting the aggregated value if present.
        stat.pop(None, None)
        devices = self.inspector.get_hardware_device(entity_metric)
        stat = _change_dev2vol(self.conf, stat, devices)
        # Stats provided from vSphere are in KB/s, converting it to B/s.
        for key in stat:
            value = stat.get(key, 0) * units.Ki
            yield key, value


class DiskReadIopsMetric(BaseMetric):
    counter_name = VC_VIRTUAL_DISK_READ_IOPS_CNTR
    instance = '*'
    gnocchi_resource_type = 'instance_disk'
    gnocchi_metric_name = 'disk.device.read.iops'

    def handle_result(self, entity_metric):
        stat = super(DiskReadIopsMetric, self).handle_result(entity_metric)
        # For some device counters, in addition to the per device value
        # the Performance manager also returns the aggregated value.
        # Just to be consistent, deleting the aggregated value if present.
        stat.pop(None, None)
        devices = self.inspector.get_hardware_device(entity_metric)
        stat = _change_dev2vol(self.conf, stat, devices)
        for key in stat:
            value = stat.get(key, 0)
            yield key, value


class DiskWriteIopsMetric(BaseMetric):
    counter_name = VC_VIRTUAL_DISK_WRITE_IOPS_CNTR
    instance = '*'
    gnocchi_resource_type = 'instance_disk'
    gnocchi_metric_name = 'disk.device.write.iops'

    def handle_result(self, entity_metric):
        stat = super(DiskWriteIopsMetric, self).handle_result(entity_metric)
        # For some device counters, in addition to the per device value
        # the Performance manager also returns the aggregated value.
        # Just to be consistent, deleting the aggregated value if present.
        stat.pop(None, None)
        devices = self.inspector.get_hardware_device(entity_metric)
        stat = _change_dev2vol(self.conf, stat, devices)
        for key in stat:
            value = stat.get(key, 0)
            yield key, value


def on_load_failure_callback(*args, **kwargs):
    raise


def load_metrics(conf):
    import stevedore
    mgr = stevedore.named.NamedExtensionManager(
            'vmware_collector.metrics',
            conf.metrics,
            on_load_failure_callback=on_load_failure_callback,
            invoke_on_load=False)

    return [e.plugin for e in mgr]


def _change_key2port(conf, stat, devices):
    ''' Replace the NIC number with the port id
    {'4000': 0.0}
    to
    {'40c99f28-16c1-4c18-8be4-b33511f737d9': 0.0}
    '''

    result = {}
    for device in devices:
        if str(device.key) in stat:
            port = neutron.get_port_by_mac(conf, device.macAddress)
            if port == []:
                LOG.warning("Can't find the port information with "
                            "this mac: %s" % device.macAddress)
                result[str(device.key)] = stat[str(device.key)]
            else:
                result[port[0]['id']] = stat[str(device.key)]
    return result


def _change_dev2vol(conf, stat, devices):
    ''' Replace the device number with the volume id
    {'scsi0:0': 0.0} or {'ide0:0': 0.0}
    to
    {'92d391a0-78da-4f9d-8007-bec3947775e7': 0.0}
    '''

    result = {}
    ide_device_key_map, scsi_device_key_map = [], []
    key_map = {device.key: index for index, device in enumerate(devices)}

    # ------------------------------------------------------------
    # |label: IDE 0                                              |
    # |  device type    : vim.vm.device.VirtualIDEController     |
    # |  backing type   : NoneType                               |
    # |  key            : 200                                    |
    # |  summary        : IDE 0                                  |
    # |----------------------------------------------------------|
    # |label: SCSI controller 0                                  |
    # |  device type    : vim.vm.device.VirtualLsiLogicController|
    # |  backing type   : NoneType                               |
    # |  key            : 1000                                   |
    # |  summary        : LSI Logic                              |
    # ------------------------------------------------------------
    # TODO (The controller cannot be created in openstack,
    #       so the default controller <SCSI 0/IDE 0> is fixed here)
    controller_keys = {200: ide_device_key_map, 1000: scsi_device_key_map}

    for key in controller_keys:
        if key_map.get(key) is not None and hasattr(
            devices[key_map.get(key)], 'device'):
            controller_keys[key].extend(devices[key_map[key]].device)

    def _regular_search(fileName):
        result = re.search(utils.UUID_RE, fileName, re.IGNORECASE)
        if not result:
            LOG.warning('There is no uuid format string in filename: %s' %
                        fileName)
            return result
        else:
            return result.group()

    # Return value:
    # --------------------------------------------
    # | Value | Description                      |
    # |------------------------------------------|
    # | None  | We don't process the raw data    |
    # |'root' | Mark root disk                   |
    # | uuid  | Volume id in Openstack           |
    # --------------------------------------------
    def _parse_backing_filename(device):
        if (device.deviceInfo['label'].encode('utf-8') in
            translation_mapping['root']):
            LOG.debug('The current device is Root Disk')
            fileName = device.backing.fileName
            if 'volume' in fileName:
                LOG.debug('The root disk is mounted from openstack')
                volume_id = _regular_search(fileName) or 'root'
                return volume_id
            else:
                return 'root'
        elif not [dev_name for dev_name in translation_mapping['cd_dvd']
                  if dev_name in device.deviceInfo['label'].encode('utf-8')]:
            LOG.debug('The current device is VirtualDisk')
            fileName = device.backing.fileName
            if 'volume' in fileName:
                LOG.debug('The current device is VirtualDisk '
                          'mounted from openstack, the fileName is %s' %
                          fileName)
                volume_id = _regular_search(fileName)
                return volume_id
            else:
                LOG.warning('The current device is VirtualDisk '
                            'mounted from vmware, the fileName is %s' %
                            fileName)
                return None
        return None

    def _combined_port_number(type, unitNumber):
        type_map = {"scsi": "scsi0:",
                    "ide": "ide0:"}
        return type_map[type] + str(unitNumber)

    for device_key in (ide_device_key_map + scsi_device_key_map):
        device = devices[key_map[device_key]]
        volume_id = _parse_backing_filename(device)
        if volume_id:
            device_type = 'ide' if device_key in ide_device_key_map else 'scsi'
            stat_key = _combined_port_number(
                device_type, devices[key_map[device_key]].unitNumber)
            result[volume_id] = stat[stat_key]
        # We don't process the raw data
        else:
            LOG.warning('We do not process the raw data, the fileName in '
                        'vmware is %s' % device.backing.fileName)
            result = stat
    return result
