from oslo_log import log

from vmware_collector.common import constants
from vmware_collector.sync import base


LOG = log.getLogger(__name__)


class SyncManager(object):

    sort_process_list = [
        constants.RT_INSTANCE_DISK,
        constants.RT_INSTANCE_NETWORK_INTERFACE
    ]

    def __init__(self, conf):
        self.conf = conf
        self.base = base.SyncOperation(self.conf)

    # The main flow of synchronization resource information
    def sync(self):
        # Batch processing
        resources_attribute = self.base.get_resources_attribute('instance')
        instances_info = self.base.get_instances_attached_info()

        resource_ids = {resource_attribute.get('id') for
                        resource_attribute in resources_attribute}
        instances_ids = {instance_info.get('id') for
                         instance_info in instances_info}

        del_ids = resource_ids - instances_ids

        # Sort processing
        resources_attribute = []
        attached_set = set()

        for resource_type in self.sort_process_list:
            resources_attribute += self.base.get_resources_attribute(
                resource_type)

        original_resource_set = {resource_attribute.get('original_resource_id')
                                 for resource_attribute in resources_attribute}
        for instance_info in instances_info:
            attached_set |= set(instance_info.get('volume_ids'))
            attached_set |= set(instance_info.get('port_ids'))
        del_set = original_resource_set - attached_set

        mapping = {resource_attribute.get('original_resource_id'):
                   resource_attribute.get('id') for
                   resource_attribute in resources_attribute}
        del_ids |= {mapping[del_indiv] for del_indiv in del_set}

        self.base.delete_resources(del_ids)
