import datetime


def now():
    return datetime.datetime.now()


def format_date(date):
    return date.strftime('%Y-%m-%dT%H:%M:%d')
