from vmware_collector.common import utils


RES_TYPE_INSTANCE = 'instance'
RES_TYPE_INSTANCE_NETWORK_INTERFACE = 'instance_network_interface'
RES_TYPE_INSTANCE_DISK = 'instance_disk'


class ReousrceMetric(object):

    def __init__(self,
                 instance_id,
                 metric_name,
                 value,
                 timestamp=None,
                 resource_name=None,
                 resource_type='instance'):
        self.instance_id = instance_id
        self.metric_name = metric_name
        self.value = value
        self.timestamp = timestamp
        self.resource_name = resource_name
        self.resource_type = resource_type

        if not self.timestamp:
            self.timestamp = utils.now()

    @property
    def original_resource_id(self):
        if self.resource_type in [RES_TYPE_INSTANCE_DISK,
                                  RES_TYPE_INSTANCE_NETWORK_INTERFACE]:
            return '%s-%s' % (self.instance_id, self.resource_name)
        else:
            return self.instance_id

    def to_metric(self):
        return {
            self.metric_name: [{
                'value': self.value,
                'timestamp': utils.format_date(self.timestamp)
            }]
        }

    # NOTE(jeffrey4l) gnocchi >= 4.2 api changed here
    def to_metric_v42(self):
        return {
            self.metric_name: {
                'measures': [{
                    'value': self.value,
                    'timestamp': utils.format_date(self.timestamp)
                }]
            }
        }
