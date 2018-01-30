import logging

from gnocchiclient import exceptions as gnocchi_exc
from gnocchiclient import client

from vmware_collector import nova
from vmware_collector import keystone


LOG = logging.getLogger(__name__)


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

    def handler_instance_stats(self, instance_stats):
        measures = {}
        for instance_stat in instance_stats:
            measures.update(self._handle_instance_stat(instance_stat))
        self.client.metric.batch_resources_metrics_measures(
                measures,
                create_metrics=True)
        LOG.info('Pushed measures for instance: %s', instance_stats)

    def _handle_instance_stat(self, instance_stat):
        resource = self.get_resource(instance_stat)
        measures = instance_stat.to_measures()
        return {resource['id']: measures}

    def get_server_info(self, uuid):
        server = self._instance_cache.get(uuid)
        if not server:
            server = self.novaclient.servers.get(uuid)
            self._instance_cache[uuid] = server
        return server

    def get_resource(self, instance_stat):
        resource_id = instance_stat.uuid
        if self._resource_cache.get(resource_id):
            return self._resource_cache.get(resource_id)

        server = self.get_server_info(instance_stat.uuid)
        params = {
            'id': server.id,
            'display_name': server.name,
            'flavor_id': server.flavor['id'],
            'host': getattr(server, 'OS-EXT-SRV-ATTR:host'),
            'image_ref': server.image['id'],
            'server_group': ''  # TODO
        }
        LOG.debug('Creating resource: %s %s', resource_id, params)
        try:
            rt = self.client.resource.create('instance', params)
        except gnocchi_exc.ResourceAlreadyExists:
            rt = self.client.resource.get('instance', instance_stat.uuid)
        self._resource_cache[resource_id] = rt
        return rt

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
