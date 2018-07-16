import iso8601
import sys

from oslo_config import cfg
from oslo_log import log

from gnocchiclient import client
from gnocchiclient import exceptions as gnocchi_exc

from vmware_collector.common import constants
from vmware_collector.common import exceptions
from vmware_collector.common import opts
from vmware_collector.common import utils
from vmware_collector.services import keystone
from vmware_collector.services import nova


LOG = log.getLogger(__name__)


gnocchi_helper = None


# NOTE(sileht): This is the initial resource types created in Gnocchi
# This list must never change to keep in sync with what Gnocchi early
# database contents was containing
resources_initial = {
    "image": {
        "name": {"type": "string", "min_length": 0, "max_length": 255,
                 "required": True},
        "container_format": {"type": "string", "min_length": 0,
                             "max_length": 255, "required": True},
        "disk_format": {"type": "string", "min_length": 0, "max_length": 255,
                        "required": True},
    },
    "instance": {
        "flavor_id": {"type": "string", "min_length": 0, "max_length": 255,
                      "required": True},
        "image_ref": {"type": "string", "min_length": 0, "max_length": 255,
                      "required": False},
        "host": {"type": "string", "min_length": 0, "max_length": 255,
                 "required": True},
        "display_name": {"type": "string", "min_length": 0, "max_length": 255,
                         "required": True},
        "server_group": {"type": "string", "min_length": 0, "max_length": 255,
                         "required": False},
    },
    "instance_disk": {
        "name": {"type": "string", "min_length": 0, "max_length": 255,
                 "required": True},
        "instance_id": {"type": "uuid", "required": True},
    },
    "instance_network_interface": {
        "name": {"type": "string", "min_length": 0, "max_length": 255,
                 "required": True},
        "instance_id": {"type": "uuid", "required": True},
    },
    "volume": {
        "display_name": {"type": "string", "min_length": 0, "max_length": 255,
                         "required": False},
    },
    "swift_account": {},
    "ceph_account": {},
    "network": {},
    "identity": {},
    "ipmi": {},
    "stack": {},
    "host": {
        "host_name": {"type": "string", "min_length": 0, "max_length": 255,
                      "required": True},
    },
    "host_network_interface": {
        "host_name": {"type": "string", "min_length": 0, "max_length": 255,
                      "required": True},
        "device_name": {"type": "string", "min_length": 0, "max_length": 255,
                        "required": False},
    },
    "host_disk": {
        "host_name": {"type": "string", "min_length": 0, "max_length": 255,
                      "required": True},
        "device_name": {"type": "string", "min_length": 0, "max_length": 255,
                        "required": False},
    },
}


# NOTE(sileht): Order matter this have to be considered like alembic migration
# code, because it updates the resources schema of Gnocchi
resources_update_operations = [
    {"desc": "add volume_type to volume",
     "type": "update_attribute_type",
     "resource_type": "volume",
     "data": [{
         "op": "add",
         "path": "/attributes/volume_type",
         "value": {"type": "string", "min_length": 0, "max_length": 255,
                   "required": False}
     }]},
    {"desc": "add flavor_name to instance",
     "type": "update_attribute_type",
     "resource_type": "instance",
     "data": [{
         "op": "add",
         "path": "/attributes/flavor_name",
         "value": {"type": "string", "min_length": 0, "max_length": 255,
                   "required": True, "options": {'fill': ''}}
     }]},
    {"desc": "add nova_compute resource type",
     "type": "create_resource_type",
     "resource_type": "nova_compute",
     "data": [{
         "attributes": {"host_name": {"type": "string", "min_length": 0,
                        "max_length": 255, "required": True}}
     }]},
    {"desc": "add manila share type",
     "type": "create_resource_type",
     "resource_type": "manila_share",
     "data": [{
         "attributes": {"name": {"type": "string", "min_length": 0,
                                 "max_length": 255, "required": False},
                        "host": {"type": "string", "min_length": 0,
                                 "max_length": 255, "required": True},
                        "protocol": {"type": "string", "min_length": 0,
                                     "max_length": 255, "required": False},
                        "availability_zone": {"type": "string",
                                              "min_length": 0,
                                              "max_length": 255,
                                              "required": False},
                        "status": {"type": "string", "min_length": 0,
                                   "max_length": 255,
                                   "required": True}}
     }]},
    {"desc": "add switch resource type",
     "type": "create_resource_type",
     "resource_type": "switch",
     "data": [{
         "attributes": {"controller": {"type": "string", "min_length": 0,
                                       "max_length": 255, "required": True}}
     }]},
    {"desc": "add switch_port resource type",
     "type": "create_resource_type",
     "resource_type": "switch_port",
     "data": [{
         "attributes": {"switch": {"type": "string", "min_length": 0,
                                   "max_length": 64, "required": True},
                        "port_number_on_switch": {"type": "number", "min": 0,
                                                  "max": 4294967295,
                                                  "required": False},
                        "neutron_port_id": {"type": "string",
                                            "min_length": 0,
                                            "max_length": 255,
                                            "required": False},
                        "controller": {"type": "string", "min_length": 0,
                                       "max_length": 255, "required": True}}
     }]},
    {"desc": "add port resource type",
     "type": "create_resource_type",
     "resource_type": "port",
     "data": [{
         "attributes": {"controller": {"type": "string", "min_length": 0,
                                       "max_length": 255, "required": True}}
     }]},
    {"desc": "add switch_table resource type",
     "type": "create_resource_type",
     "resource_type": "switch_table",
     "data": [{
         "attributes": {"switch": {"type": "string", "min_length": 0,
                                   "max_length": 64, "required": True},
                        "controller": {"type": "string", "min_length": 0,
                                       "max_length": 255, "required": True}}
     }]},
]


def get_gnocchiclient(conf):
    session = keystone.get_session(conf)
    return client.Client('1', session=session)


class GnocchiHelper(object):

    def __init__(self, conf):
        self.conf = conf
        self.client = get_gnocchiclient(self.conf)
        self.novaclient = nova.get_nova_client(self.conf)
        self._resource_cache = {}
        self._instance_cache = {}

    def get_server_info(self, instance_id):
        server = self._instance_cache.get(instance_id)
        if not server:
            server = self.novaclient.servers.get(instance_id)
            self._instance_cache[instance_id] = server
        return server

    def get_resource(self, metric):
        if metric.resource_type == constants.RT_INSTANCE:
            resource = self.get_instance_resource(metric.instance_id)
        elif metric.resource_type == constants.RT_INSTANCE_DISK:
            resource = self.get_instance_disk_resource(metric.instance_id,
                                                       metric.resource_name)
        elif (metric.resource_type ==
                constants.RT_INSTANCE_NETWORK_INTERFACE):
            resource = self.get_instance_network_resource(
                metric.instance_id,
                metric.resource_name)
        return resource

    def get_resources(self, resource_type):
        return self.client.resource.list(resource_type)

    def delete_resource(self, resource_id, hard=False):
        if hard:
            self.client.resource.delete(resource_id)
        else:
            now = utils.now().replace(tzinfo=iso8601.iso8601.UTC)
            update_dic = {'ended_at': now}
            self.client.resource.update('generic', resource_id, update_dic)

    def get_instance_resource(self, instance_id):
        server = self.get_server_info(instance_id)
        params = {
            'id': server.id,
            'display_name': server.name,
            'flavor_name': server.flavor['id'],
            'flavor_id': server.flavor['id'],
            'host': getattr(server, 'OS-EXT-SRV-ATTR:host'),
            'image_ref': server.image['id'],
            'server_group': ''  # TODO
        }
        return self._get_or_create_resource(instance_id, 'instance', params)

    def get_instance_disk_resource(self, instance_id, name):
        _id = '%s-%s' % (instance_id, name)
        params = {
            'id': _id,
            'instance_id': instance_id,
            'name': name
        }
        return self._get_or_create_resource(_id,
                                            'instance_disk',
                                            params)

    def get_instance_network_resource(self, instance_id, name):
        _id = '%s-%s' % (instance_id, name)
        params = {
            'id': _id,
            'instance_id': instance_id,
            'name': name
        }
        return self._get_or_create_resource(_id,
                                            'instance_network_interface',
                                            params)

    def _get_or_create_resource(self, resource_id, resource_type, params):
        res = self._resource_cache.get(resource_id)
        if not res:
            LOG.debug('Creating resource: %s %s', resource_id, params)
            try:
                res = self.client.resource.create(resource_type, params)
            except gnocchi_exc.ResourceAlreadyExists:
                query = {
                    "=": {
                        "original_resource_id": resource_id
                    }
                }
                res = self.client.resource.search(resource_type=resource_type,
                                                  query=query)
                if res:
                    res = res[0]
                else:
                    raise exceptions.ResourceNotFound(
                        resource_id=resource_id,
                        resource_type=resource_type)
            self._resource_cache[resource_id] = res
        return res

    def get_metric(self, metric_name, instance_stat):
        resource = self.get_resource(instance_stat)
        if resource.get(metric_name):
            return resource.get(metric_name)

        try:
            metric = self.client.metric.create(name=metric_name,
                                               resource_id=instance_stat.uuid)
        except gnocchi_exc.NamedMetricAlreadyExists:
            metric = self.client.metric.get(metric_name,
                                            resource_id=instance_stat.uuid)
        resource[metric_name] = metric
        return metric


def get_gnocchi_helper(conf):
    global gnocchi_helper
    if not gnocchi_helper:
        gnocchi_helper = GnocchiHelper(conf)
    return gnocchi_helper


# NOTE(rogeryu): Copy from ceilometer here, because the initial_resource and
# update_resource will determine the current existing resources and the
# current resource have existing properties, the all exception can be covered,
# no longer modify
def upgrade():
    conf = cfg.ConfigOpts()
    opts.register_opts(conf)
    conf(sys.argv[1:])

    gnocchi = get_gnocchiclient(conf)
    for name, attributes in resources_initial.items():
        try:
            gnocchi.resource_type.get(name=name)
        except gnocchi_exc.ResourceTypeNotFound:
            LOG.info('Resource not found: %s, Creating...', name)
            rt = {'name': name, 'attributes': attributes}
            gnocchi.resource_type.create(resource_type=rt)
            LOG.info('Resource type: %s created', name)

    LOG.info('Start updating resource types')
    for ops in resources_update_operations:
        if ops['type'] == 'update_attribute_type':
            rt = gnocchi.resource_type.get(name=ops['resource_type'])
            first_op = ops['data'][0]
            attrib = first_op['path'].replace('/attributes', '')
            if first_op['op'] == 'add' and attrib in rt['attributes']:
                continue
            if first_op['op'] == 'remove' and attrib not in rt['attributes']:
                continue
            gnocchi.resource_type.update(ops['resource_type'], ops['data'])
        elif ops['type'] == 'create_resource_type':
            try:
                gnocchi.resource_type.get(name=ops['resource_type'])
            except gnocchi_exc.ResourceTypeNotFound:
                LOG.info('Resource not found: %s, Creating...',
                         ops['resource_type'])
                rt = {'name': ops['resource_type'],
                      'attributes': ops['data'][0]['attributes']}
                gnocchi.resource_type.create(resource_type=rt)
                LOG.info('Resource type: %s created', ops['resource_type'])
    LOG.info('Resource types update completed')
