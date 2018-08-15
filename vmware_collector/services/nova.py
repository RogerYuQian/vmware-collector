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
def get_all_instances(conf):
    '''Get all instances

    Get all instances by pagination
    '''
    limit = conf.vm_list_limit
    nova_client = get_nova_client(conf)

    def _get_instances(client, limit, marker=None):

        servers = []
        search_opts = {
            'all_tenants': True
        }
        servers += client.servers.list(limit=limit,
                                       marker=marker,
                                       search_opts=search_opts)
        num = len(servers)
        if num == limit:
            marker_id = servers[-1].id
            servers += _get_instances(client, limit, marker=marker_id)
        return servers

    return _get_instances(nova_client, limit)
