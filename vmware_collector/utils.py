import datetime


def now():
    return datetime.datetime.now()


def format_date(date):
    return date.strftime('%Y-%m-%dT%H:%M:%d')


def group(eles, count):
    itr = iter(eles)
    while True:
        ret = []
        try:
            for i in range(count):
                ret.append(itr.next())
            yield ret
        except StopIteration:
            if ret:
                yield ret
            raise StopIteration
