#!/usr/bin/env python2

# get all instance
# query from vmware
# push statics to mq

import collections
import sys
import logging
import datetime

from eventlet import greenpool
from eventlet import greenthread
from oslo_config import cfg

from vmware_collector import opts
from vmware_collector import nova
from vmware_collector import vmware
from vmware_collector import utils
from vmware_collector import gnocchi


LOG = logging.getLogger(__name__)


class Manager(object):
    def __init__(self, conf):
        self.conf = conf
        self.novaclient = nova.get_nova_client(conf)
        self.gnocchi_helper = gnocchi.get_gnocchi_helper(conf)
        LOG.info("Initializing inspector.")
        self.insp = vmware.VsphereInspector(self.conf)
        LOG.info("Inspector is initialized.")
        self.vm_mobjs = []
        greenthread.spawn(self.get_vm_mobjs)

    def get_all_nova_instance(self):
        return self.novaclient.servers.list()

    def get_vm_mobjs(self):
        while True:
            vm_mobjs = []
            instances = self.get_all_nova_instance()
            for instance in instances:
                vm_mobj = self.insp.get_vm_mobj(instance.id)
                if not vm_mobj:
                    continue
                vm_power_stat = self.insp.query_vm_property(
                    vm_mobj, 'runtime.powerState')
                if vm_power_stat == 'poweredOff':
                    LOG.debug('VM %s power state is off', vm_mobj)
                    continue
                vm_mobjs.append(vm_mobj)
            LOG.info('Update vm_objs to %s', [(vm.value, instance.id)
                                              for vm, instance in
                                              zip(vm_mobjs, instances)])
            # TODO add lock
            self.vm_mobjs[:] = vm_mobjs
            greenthread.sleep(self.conf.vm_cache_period)

    def query_vm_perf_stats(self, vm_mobjs):
        pool = greenpool.GreenPool(self.conf.pool_size)
        rets = []
        stats = []
        for sub_vms in utils.group(vm_mobjs, self.conf.vm_num):
            ret = pool.spawn(self.insp._query_vm_perf_stats,
                             sub_vms,
                             self.conf.interval)
            rets.append(ret)
        for r in rets:
            stats.extend(r.wait())
        return stats

    def _convert_metric_to_measure(self, metrics):
        '''
            [
                {'memory_usage': [{
                    'timestamp': '2018-xx',
                    'value': 75776.0
                    }]
                },
                {'cpu_util': [{
                    'timestamp': '2018-xx',
                    'value': 0.07
                    }]
                }
            ]

            to

            {
                83a600b8-68cd-4a17-8e67-62ec0a5ed25f: {
                    'memory_usage': [{
                        'timestamp': '2018-xx',
                        'value': 75776.0
                    }],
                    'cpu_util': [{
                        'timestamp': '2018-xx',
                        'value': 0.07
                    }]
                }
            }
        '''

        measures = collections.defaultdict(dict)
        for metric in metrics:
            resource = self.gnocchi_helper.get_resource(metric)
            measures[resource['id']].update(metric.to_metric())
        return measures

    def run_once(self):
        LOG.info('Starting to pull metrics')
        stats = self.query_vm_perf_stats(self.vm_mobjs)
        LOG.info("Get stats: %s", [m.to_metric() for m in stats])
        measures = self._convert_metric_to_measure(stats)
        LOG.info('Trying to push measures: %s', measures)
        self.gnocchi_helper.client.metric.batch_resources_metrics_measures(
            measures, create_metrics=True)
        LOG.info("All measures are pushed")

    def run(self):
        while True:
            start = utils.now()
            try:
                if not self.vm_mobjs:
                    LOG.info('No vm is found. sleep 10 seconds.')
                    greenthread.sleep(10)
                    continue
                self.run_once()
            except KeyboardInterrupt:
                LOG.info('Exiting')
                break
            except Exception:
                LOG.exception('Unkonw exception: %s')

            end = utils.now()
            period = end - start
            LOG.info('Get all metrics in %s seconds',
                     period.total_seconds())
            next_run = start + datetime.timedelta(
                    seconds=self.conf.interval)
            time_left = next_run - end
            if time_left.total_seconds() > 0:
                LOG.info('Sleep %s seconds to run next cycle',
                         time_left.total_seconds())
                greenthread.sleep(time_left.total_seconds())
            else:
                LOG.warning(('it takes too long to pull metrics then'
                             ' interval, try to increase the interval'
                             ' options'))
                greenthread.sleep(10)


def main():
    conf = cfg.ConfigOpts()
    opts.register_opts(conf)
    conf(sys.argv[1:])
    manager = Manager(conf)
    logging.basicConfig(level=logging.INFO)
    manager.run()


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    main()
