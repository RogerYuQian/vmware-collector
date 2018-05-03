from oslo_utils import units


VC_AVERAGE_MEMORY_CONSUMED_CNTR = 'mem:consumed:average'
VC_AVERAGE_CPU_CONSUMED_CNTR = 'cpu:usage:average'
VC_NETWORK_RX_COUNTER = 'net:received:average'
VC_NETWORK_TX_COUNTER = 'net:transmitted:average'
VC_DISK_READ_RATE_CNTR = "disk:read:average"
VC_DISK_READ_REQUESTS_RATE_CNTR = "disk:numberReadAveraged:average"
VC_DISK_WRITE_RATE_CNTR = "disk:write:average"
VC_DISK_WRITE_REQUESTS_RATE_CNTR = "disk:numberWriteAveraged:average"


class BaseMetric(object):
    counter_name = None
    instance = ''
    gnocchi_resource_type = None

    def __init__(self, inspector):
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
        network_tx = {}
        for vnic_id, value in stat.items():
            network_tx[vnic_id] = value * units.Ki
            yield vnic_id, value * units.Ki


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
        for vnic_id, value in stat.items():
            yield vnic_id, value * units.Ki


class DiskReadMetric(BaseMetric):
    counter_name = VC_DISK_READ_RATE_CNTR
    instance = '*'
    gnocchi_resource_type = 'instance_disk'
    gnocchi_metric_name = 'disk.device.read.bytes.rate'

    def handle_result(self, entity_metric):
        stat = super(DiskReadMetric, self).handle_result(entity_metric)
        # For some device counters, in addition to the per device value
        # the Performance manager also returns the aggregated value.
        # Just to be consistent, deleting the aggregated value if present.
        stat.pop(None, None)
        # Stats provided from vSphere are in KB/s, converting it to B/s.
        for key in stat:
            value = stat.get(key, 0) * units.Ki
            yield key, value


class DiskWriteMetric(BaseMetric):
    counter_name = VC_DISK_WRITE_RATE_CNTR
    instance = '*'
    gnocchi_resource_type = 'instance_disk'
    gnocchi_metric_name = 'disk.device.write.bytes.rate'

    def handle_result(self, entity_metric):
        stat = super(DiskWriteMetric, self).handle_result(entity_metric)
        # For some device counters, in addition to the per device value
        # the Performance manager also returns the aggregated value.
        # Just to be consistent, deleting the aggregated value if present.
        stat.pop(None, None)
        # Stats provided from vSphere are in KB/s, converting it to B/s.
        for key in stat:
            value = stat.get(key, 0) * units.Ki
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
