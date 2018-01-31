import os
from vmware_collector.tests import base as test_base

from oslo_config import cfg

from vmware_collector import vmware2
from vmware_collector import opts

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


class VmwareTest(test_base.BaseTestCase):

    def test_c(self):
        ins = vmware2.VsphereInspector(self.conf)
        ins._init_vm_mobj_lookup_map()
        ins._init_perf_counter_id_lookup_map()
        stat = ins._query_vm_perf_stats(ins._vm_mobj_lookup_map.values(), 30)
        print stat

    def test_get_nova_instance_id(self):
        ins = vmware2.VsphereInspector(self.conf)
        import pprint
        pprint.pprint(ins.get_nova_instance_id('vm-885'))


if __name__ == "__main__":
    conf = cfg.ConfigOpts()
    opts.register_opts(conf)
    conf(['--config-file', os.path.join(CUR_DIR, 'test.conf')])
    ins = vmware2.VsphereInspector(conf)
    ins._init_vm_mobj_lookup_map()
