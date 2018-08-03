import collections
import time
import weakref

from functools import wraps


class LocalCache():
    notFound = object()

    class Dict(dict):
        def __del__(self):
            pass

    def __init__(self, maxlen=10):
        self.weak = weakref.WeakValueDictionary()
        self.strong = collections.deque(maxlen=maxlen)

    @staticmethod
    def nowTime():
        return int(time.time())

    def get(self, key):
        value = self.weak.get(key, self.notFound)
        if value is not self.notFound:
            expire = value[r'expire']
            if self.nowTime() > expire:
                return self.notFound
            else:
                return value
        else:
            return self.notFound

    def set(self, key, value):
        self.weak[key] = strongRef = LocalCache.Dict(value)
        self.strong.append(strongRef)

def mem_cache(expire=0):
    caches = LocalCache()

    def _wrappend(func):
        @wraps(func)
        def __wrapped(*args, **kwargs):
            key = str(func) + str(args) + str(kwargs)
            result = caches.get(key)
            if result is LocalCache.notFound:
                value = func(*args, **kwargs)
                caches.set(key, {"value": value,
                                 "expire": expire + caches.nowTime()})
                result = caches.get(key)
                return value
            else:
                return result["value"]
        return __wrapped
    return _wrappend
