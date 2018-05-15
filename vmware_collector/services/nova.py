# -*- coding:utf-8 -*-

from novaclient import client

from vmware_collector.services import keystone


def get_nova_client(conf, api_version='2.29'):
    '''Get nova client

    2.29 support evacuate with host parameter
    '''
    sess = keystone.get_session(conf)

    return client.Client(
        api_version,
        session=sess,
        endpoint_type='internal',
        region_name='RegionOne')


# cache the returns
def get_all_instances(conf, marker=None, limit=None):

    nova_client = get_nova_client(conf)
    return nova_client.servers.list(marker=marker, limit=limit)
