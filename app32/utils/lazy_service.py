"""Deferred singleton construction without database work during module import."""
from threading import RLock
from werkzeug.local import LocalProxy


def lazy_service(factory):
    lock = RLock()
    instance = []
    def resolve():
        with lock:
            if not instance:
                instance.append(factory())
            return instance[0]
    return LocalProxy(resolve)
