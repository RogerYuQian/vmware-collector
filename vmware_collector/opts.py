# -*- coding:utf-8 -*-
from oslo_config import cfg

from keystoneauth1.loading import conf as keystone_conf


OPTS = [
]

VMWARE_OPTS = [
    cfg.StrOpt('host'),
    cfg.StrOpt('username'),
    cfg.StrOpt('password'),
    cfg.IntOpt('port', default=443)
]


def register_opts(conf):
    conf.register_opts(OPTS)
    keystone_conf.register_conf_options(conf, 'keystone_authtoken')
    conf.register_opts(VMWARE_OPTS, 'vmware')
