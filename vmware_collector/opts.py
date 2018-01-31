# -*- coding:utf-8 -*-
from oslo_config import cfg

from keystoneauth1.loading import conf as keystone_conf


OPTS = [
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


def register_opts(conf):
    conf.register_opts(OPTS)
    keystone_conf.register_conf_options(conf, 'keystone_authtoken')
    conf.register_opts(OPTS, 'vmware')
