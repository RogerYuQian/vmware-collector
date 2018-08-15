# -*- coding:utf-8 -*-
from oslo_config import cfg

from keystoneauth1.loading import conf as keystone_conf

OPTS = [
    cfg.IntOpt('interval', default=300,
               help='Pull metric interval'),
    cfg.IntOpt('pool_size', default=10,
               help='Vsphere pool size'),
    cfg.IntOpt('vm_num', default=10,
               help='the number of vms when pulling metrics'),
    cfg.IntOpt('vm_cache_period', default=600,
               help='the period of the vm is cached'),
    cfg.ListOpt('metrics', default=['cpu']),
    cfg.BoolOpt('hard_delete', default=False,
                help='If true, the unchecked resources will be '
                     'automatically deleted. If false, only flag '
                     'their status as deleted'),
    cfg.IntOpt('vm_list_limit', default=100,
               help='The number of vm for each list')
]

VMWARE_OPTS = [
    cfg.HostAddressOpt('host_ip',
                       default='127.0.0.1',
                       help='IP address of the VMware vSphere host.'),
    cfg.PortOpt('host_port',
                default=443,
                help='Port of the VMware vSphere host.'),
    cfg.StrOpt('host_username',
               default='',
               help='Username of VMware vSphere.'),
    cfg.StrOpt('host_password',
               default='',
               help='Password of VMware vSphere.',
               secret=True),
    cfg.StrOpt('ca_file',
               help='CA bundle file to use in verifying the vCenter server '
                    'certificate.'),
    cfg.BoolOpt('insecure',
                default=False,
                help='If true, the vCenter server certificate is not '
                     'verified. If false, then the default CA truststore is '
                     'used for verification. This option is ignored if '
                     '"ca_file" is set.'),
    cfg.IntOpt('api_retry_count',
               default=10,
               help='Number of times a VMware vSphere API may be retried.'),
    cfg.FloatOpt('task_poll_interval',
                 default=0.5,
                 help='Sleep time in seconds for polling an ongoing async '
                      'task.'),
    cfg.StrOpt('wsdl_location',
               help='Optional vim service WSDL location '
                    'e.g http://<server>/vimService.wsdl. '
                    'Optional over-ride to default location for bug '
                    'work-arounds.'),
]

COORDINATION_OPTS = [
    cfg.StrOpt('backend_url',
               help='The backend URL to use for distributed coordination. If '
               'left empty, per-deployment central agent and per-host '
               'compute agent won\'t do workload '
               'partitioning and will only function correctly if a '
               'single instance of that service is running.'),
    cfg.IntOpt('sync_rate',
               default=30,
               help='Coordinator listening period'),
]


def register_opts(conf):
    conf.register_opts(OPTS)
    keystone_conf.register_conf_options(conf, 'keystone_authtoken')
    conf.register_opts(VMWARE_OPTS, 'vmware')
    conf.register_opts(COORDINATION_OPTS, 'coordination')
