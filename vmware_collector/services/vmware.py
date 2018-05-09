import logging
from oslo_vmware import vim_util
from vmware_collector import metrics
from vmware_collector import objects

PERF_MANAGER_TYPE = "PerformanceManager"
PERF_COUNTER_PROPERTY = "perfCounter"
VM_INSTANCE_ID_PROPERTY = 'config.extraConfig["nvp.vm-uuid"].value'

LOG = logging.getLogger(__name__)

# ESXi Servers sample performance data every 20 seconds. 20-second interval
# data is called instance data or real-time data. To retrieve instance data,
# we need to specify a value of 20 seconds for the "PerfQuerySpec.intervalId"
# property. In that case the "QueryPerf" method operates as a raw data feed
# that bypasses the vCenter database and instead retrieves performance data
# from an ESXi host.
# The following value is time interval for real-time performance stats
# in seconds and it is not configurable.
VC_REAL_TIME_SAMPLING_INTERVAL = 20


vmware_api = None


def get_api_session(conf):
    global vmware_api
    if vmware_api is None:
        vmware_api = __import__('oslo_vmware.api')
    api_session = vmware_api.api.VMwareAPISession(
        conf.vmware.host_ip,
        conf.vmware.host_username,
        conf.vmware.host_password,
        conf.vmware.api_retry_count,
        conf.vmware.task_poll_interval,
        wsdl_loc=conf.vmware.wsdl_location,
        port=conf.vmware.host_port,
        cacert=conf.vmware.ca_file,
        insecure=conf.vmware.insecure)
    return api_session


class VsphereInspector(object):

    def __init__(self, conf):
        self.conf = conf

        self._api_session = get_api_session(conf)

        # Mapping between "VM's Nova instance Id" -> "VM's managed object"
        # In case a VM is deployed by Nova, then its name is instance ID.
        # So this map essentially has VM names as keys.
        self._vm_mobj_lookup_map = {}

        # Mapping betwwen vm_name -> instance id
        self._vm_name_lookup_map = {}

        self._perf_counter_id_lookup_map = {}

        self._max_objects = 1000

        metrics_class = metrics.load_metrics(self.conf)
        self.metrics = [clazz(self.conf, self) for clazz in metrics_class]

    def _init_vm_mobj_lookup_map(self):
        session = self._api_session
        result = session.invoke_api(vim_util, "get_objects", session.vim,
                                    "VirtualMachine", self._max_objects,
                                    [VM_INSTANCE_ID_PROPERTY],
                                    False)
        while result:
            for object in result.objects:
                vm_mobj = object.obj
                # propSet will be set only if the server provides value
                if hasattr(object, 'propSet') and object.propSet:
                    vm_instance_id = object.propSet[0].val
                    if vm_instance_id:
                        self._vm_mobj_lookup_map[vm_instance_id] = vm_mobj

            result = session.invoke_api(vim_util, "continue_retrieval",
                                        session.vim, result)

    def get_vm_mobj(self, vm_instance_id):
        """Method returns VC mobj of the VM by its NOVA instance ID."""
        if vm_instance_id not in self._vm_mobj_lookup_map:
            self._init_vm_mobj_lookup_map()

        return self._vm_mobj_lookup_map.get(vm_instance_id, None)

    def get_nova_instance_id(self, vm_name):
        if vm_name not in self._vm_name_lookup_map:
            self._init_vm_mobj_lookup_map()
            for uuid, vm_mobj in self._vm_mobj_lookup_map.items():
                self._vm_name_lookup_map[vm_mobj.value] = uuid
        return self._vm_name_lookup_map.get(vm_name, None)

    def get_hardware_device(self, entity_metric):
        session = self._api_session
        properties = ["config.hardware.device"]
        vm_instance_id = self.get_nova_instance_id(
            entity_metric.entity.value)
        vm_ref = self.get_vm_mobj(vm_instance_id)
        props = session.invoke_api(vim_util, "get_object_properties_dict",
                                   session.vim, vm_ref,
                                   properties)
        devices = props[properties[0]].VirtualDevice
        return devices

    def _init_perf_counter_id_lookup_map(self):

        # Query details of all the performance counters from VC
        session = self._api_session
        client_factory = session.vim.client.factory
        perf_manager = session.vim.service_content.perfManager

        prop_spec = vim_util.build_property_spec(
            client_factory, PERF_MANAGER_TYPE, [PERF_COUNTER_PROPERTY])

        obj_spec = vim_util.build_object_spec(
            client_factory, perf_manager, None)

        filter_spec = vim_util.build_property_filter_spec(
            client_factory, [prop_spec], [obj_spec])

        options = client_factory.create('ns0:RetrieveOptions')
        options.maxObjects = 1

        prop_collector = session.vim.service_content.propertyCollector
        result = session.invoke_api(session.vim, "RetrievePropertiesEx",
                                    prop_collector, specSet=[filter_spec],
                                    options=options)

        perf_counter_infos = result.objects[0].propSet[0].val.PerfCounterInfo

        # Extract the counter Id for each counter and populate the map
        self._perf_counter_id_lookup_map = {}
        for perf_counter_info in perf_counter_infos:

            counter_group = perf_counter_info.groupInfo.key
            counter_name = perf_counter_info.nameInfo.key
            counter_rollup_type = perf_counter_info.rollupType
            counter_id = perf_counter_info.key

            counter_full_name = (counter_group + ":" + counter_name + ":" +
                                 counter_rollup_type)
            self._perf_counter_id_lookup_map[counter_full_name] = counter_id

    def get_perf_counter_id(self, counter_full_name):
        """Method returns the ID of VC performance counter by its full name.

        A VC performance counter is uniquely identified by the
        tuple {'Group Name', 'Counter Name', 'Rollup Type'}.
        It will have an id - counter ID (changes from one VC to another),
        which is required to query performance stats from that VC.
        This method returns the ID for a counter,
        assuming 'CounterFullName' => 'Group Name:CounterName:RollupType'.
        """
        if not self._perf_counter_id_lookup_map:
            self._init_perf_counter_id_lookup_map()
        return self._perf_counter_id_lookup_map[counter_full_name]

    # TODO(akhils@vmware.com) Move this method to common library
    # when it gets checked-in
    def query_vm_property(self, vm_mobj, property_name):
        """Method returns the value of specified property for a VM.

        :param vm_mobj: managed object of the VM whose property is to be
            queried
        :param property_name: path of the property
        """
        session = self._api_session
        return session.invoke_api(vim_util, "get_object_property",
                                  session.vim, vm_mobj, property_name)

    def _query_vm_perf_stats(self, vm_mobjs, duration):
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
        session = self._api_session
        client_factory = session.vim.client.factory

        metric_ids = [m.get_metric() for m in self.metrics]

        query_specs = []
        for vm_mobj in vm_mobjs:
            query_spec = client_factory.create('ns0:PerfQuerySpec')
            query_spec.entity = vm_mobj
            query_spec.metricId = metric_ids
            query_spec.intervalId = VC_REAL_TIME_SAMPLING_INTERVAL
            # We query all samples which are applicable over the specified
            # duration
            samples_cnt = (int(duration / VC_REAL_TIME_SAMPLING_INTERVAL)
                           if duration and
                           duration >= VC_REAL_TIME_SAMPLING_INTERVAL else 1)
            query_spec.maxSample = samples_cnt
            query_specs.append(query_spec)

        perf_manager = session.vim.service_content.perfManager
        perf_stats = session.invoke_api(session.vim, 'QueryPerf', perf_manager,
                                        querySpec=query_specs)

        measures = []
        if perf_stats:
            for entity_metric in perf_stats:
                sample_infos = entity_metric.sampleInfo
                vm_name = entity_metric.entity.value
                instance_id = self.get_nova_instance_id(vm_name)
                if not sample_infos or len(sample_infos) == 0:
                    continue
                for m in self.metrics:
                    data = m.handle_result(entity_metric)
                    for name, value in data:
                        measure = objects.ReousrceMetric(
                            instance_id,
                            m.gnocchi_metric_name,
                            value,
                            resource_name=name,
                            resource_type=m.gnocchi_resource_type)
                        measures.append(measure)
        return measures
