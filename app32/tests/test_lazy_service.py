from concurrent.futures import ThreadPoolExecutor
from utils.lazy_service import lazy_service


def test_deferred_once_under_concurrency():
    calls=[]
    class Service:
        value=42
    def factory():
        calls.append(True)
        return Service()
    service=lazy_service(factory)
    assert calls == []
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert list(pool.map(lambda _:service.value,range(20))) == [42]*20
    assert len(calls)==1


def test_failed_initialization_can_retry():
    calls=[]
    def factory():
        calls.append(True)
        if len(calls)==1: raise ValueError('unavailable')
        return type('Service',(),{'value':1})()
    service=lazy_service(factory)
    import pytest
    with pytest.raises(ValueError): _=service.value
    assert service.value==1
