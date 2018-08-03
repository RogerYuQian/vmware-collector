# -*- coding:utf-8 -*-

from neutronclient.v2_0 import client
from vmware_collector.common.localcache import mem_cache
from vmware_collector.services import keystone


def get_neutron_client(conf):
    '''Get neutron client

    '''
    session = keystone.get_session(conf)

    return client.Client(
        session=session,
        endpoint_type='internal',
        region_name='RegionOne')


# cache the returns
@mem_cache(3600)
def get_port_by_mac(conf, mac_address):

    neutron_client = get_neutron_client(conf)
    resp = neutron_client.list_ports(mac_address=mac_address)
    return resp.get('ports')
