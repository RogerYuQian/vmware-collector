from vmware_collector.tests import base as test_base
from vmware_collector.services import gnocchi

from gnocchiclient import exceptions as gnocchi_exc


class TestGetGnocchiClient(test_base.BaseTestCase):
    conf_name = 'test2.conf'

    def test_get_gnocchiclient(self):
        gnocchi_client = gnocchi.get_gnocchiclient(self.conf)
        for rt in gnocchi_client.resource_type.list():
            print((rt['name'], rt))

    def test_create_resource_type(self):
        gnocchi_client = gnocchi.get_gnocchiclient(self.conf)
        id = '6b3f8e86-5c18-4fc6-b714-5ee9df3f34ba'
        params = {
            'id': '6b3f8e86-5c18-4fc6-b714-5ee9df3f34ba',
            'instance_id': '6b3f8e86-5c18-4fc6-b714-5ee9df3f34ba',
            'name': 'fake_instance',
        }
        try:
            rt = gnocchi_client.resource.create('instance_disk', params)
        except gnocchi_exc.ResourceAlreadyExists:
            rt = gnocchi_client.resource.get('instance_disk', id)
        print('resource %s is created', rt)

        try:
            metric = gnocchi_client.metric.create(name='test_metric',
                                                  resource_id=id)
            print(metric)
        except gnocchi_exc.NamedMetricAlreadyExists:
            print('metric is created')

        metric_id = 'e43d4158-3005-440f-a0ab-4d56d30cb6a7'
        import datetime
        now = datetime.datetime.now()
        data = [
            {
                'timestamp': now.strftime('%Y-%m-%dT%H:%M:%d'),
                'value': 123
                }
        ]
        ret = gnocchi_client.metric.add_measures(metric_id, data)
        print(ret)
