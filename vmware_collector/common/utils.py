import json
import datetime
import six
import socket
import tenacity
import uuid

from oslo_log import log
from tooz import coordination


LOG = log.getLogger(__name__)


def now():
    return datetime.datetime.now()


def format_date(date):
    return date.strftime('%Y-%m-%dT%H:%M:%S')


def group(eles, count):
    itr = iter(eles)
    while True:
        ret = []
        try:
            for i in range(count):
                ret.append(six.next(itr))
            yield ret
        except StopIteration:
            if ret:
                yield ret
            raise StopIteration


class DatetimeEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return format_date(obj)
        return json.JSONEncoder.default(self, obj)


def json_dumps(*args, **kwargs):
    kwargs['cls'] = DatetimeEncoder
    return json.dumps(*args, **kwargs)


def current_id():
    return "%s.%s" % (socket.gethostname(),
                      str(uuid.uuid4()))

# Retry with exponential backoff for up to 1 minute
retry = tenacity.retry(
    wait=tenacity.wait_exponential(multiplier=0.5, max=60),
    # Never retry except when explicitly asked by raising TryAgain
    retry=tenacity.retry_never,
    reraise=True)


@retry
def _enable_coordination(coord):
    try:
        coord.start(start_heart=True)
    except Exception as e:
        LOG.error("Unable to start coordinator: %s", e)
        raise tenacity.TryAgain(e)


def get_coordinator_and_start(url):
    cur_id = current_id()
    coord = coordination.get_coordinator(url, cur_id)
    _enable_coordination(coord)
    return coord, cur_id


def uuid2int(uuid):
    uuid = uuid.split('-')
    return int(''.join(uuid), 16)
