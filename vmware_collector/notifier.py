import oslo_messaging
from oslo_messaging.notify import notifier


def get_notifier(conf):
    transport = notifier.get_notification_transport(conf)
    return oslo_messaging.Notifier(
        transport,
        driver='messageingv2',
        publisher_id='vmware_collector',
        topics=['sample']
        )


def send_batch(notifier, topic, batch):
    notifier.sample({}, event_type=topic, payload=batch)
