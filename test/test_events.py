from aatest.events import Events

__author__ = 'roland'


def test_store_event():
    events = Events()
    events.store('foo', 'bar')
    assert len(events) == 1
    val = events.get('foo')[0]
    assert val.data == 'bar'


def test_print_event():
    events = Events()
    events.store('foo', 'bar')
    val = events.get('foo')[0]
    s = '{}'.format(val)
    assert s