import json
import datetime
import six


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
