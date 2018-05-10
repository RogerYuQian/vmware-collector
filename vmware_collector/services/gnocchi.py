from oslo_log import log

from gnocchiclient import client
from gnocchiclient import exceptions as gnocchi_exc

from vmware_collector.common import constants
from vmware_collector.common import exceptions
from vmware_collector.services import keystone
from vmware_collector.services import nova


LOG = log.getLogger(__name__)


gnocchi_helper = None


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

    def get_metric(self, metric_name,  instance_stat):
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
