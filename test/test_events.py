from aatest.interaction import Action
from aatest.contenthandler import HandlerResponse
import pytest
from aatest.events import Event
from aatest.events import Events

__author__ = 'roland'


def _eq(l1, l2):
    return set(l1) == set(l2)


def test_print_event():
    ev = Event(data='abc')
    s = '{}'.format(ev)
    assert len(s.split(':')) == 3


class TestEvents():
    @pytest.fixture(autouse=True)
    def setup_consumer(self):
        self.events = Events()

    def test_store_event(self):
        i = self.events.store('foo', 'bar')
        assert i

    def test_by_index(self):
        i = self.events.store('foo', 'bar')
        ev = self.events.by_index(i)
        assert ev.typ == 'foo'
        assert ev.data == 'bar'

    def test_by_ref(self):
        i = self.events.store('foo', 'bar')
        self.events.store('foo', 'bav', i)
        evl = self.events.by_ref(i)
        assert len(evl) == 1

    def test_get(self):
        self.events.store('foo', 'bar')
        evl = self.events.get('foo')
        assert len(evl) == 1
        assert evl[0].data == 'bar'

        self.events.store('foo', 'bav')
        evl = self.events.get('foo')
        assert len(evl) == 2

    def test_get_data(self):
        self.events.store('foo', 'bar')
        self.events.store('foo', 'bav')
        dl = self.events.get_data('foo')
        assert _eq(dl, ['bar', 'bav'])

    def test_get_messages(self):
        self.events.store('response', HandlerResponse(True))
        self.events.store('response', Action(None))
        self.events.store('response', HandlerResponse(True, user_action='OK'))

        mesg = self.events.get_messages('response', HandlerResponse)
        assert len(mesg) == 2

    def test_last(self):
        self.events.store('response', HandlerResponse(True))
        self.events.store('response', Action(None))
        self.events.store('response', HandlerResponse(True, user_action='OK'))

        ev = self.events.last('response')
        assert isinstance(ev, Event)
        assert isinstance(ev.data, HandlerResponse)
        assert ev.data.content_processed == True
        assert ev.data.user_action == 'OK'

    def test_get_message(self):
        self.events.store('response', HandlerResponse(True))
        self.events.store('response', HandlerResponse(True, user_action='OK'))
        self.events.store('response', Action(None))

        hr = self.events.get_message('response', HandlerResponse)
        assert isinstance(hr, HandlerResponse)
        assert hr.content_processed == True
        assert hr.user_action == 'OK'

    def test_last_item(self):
        self.events.store('index', 0)
        self.events.store('index', 1)
        self.events.store('index', 2)

        i = self.events.last_item('index')
        assert i == 2

    def test_len(self):
        self.events.store('index', 0)
        assert len(self.events) == 1
        self.events.store('index', 1)
        assert len(self.events) == 2
        self.events.store('index', 2)
        assert len(self.events) == 3

    def test_iter(self):
        self.events.store('index', 0)
        self.events.store('index', 1)
        self.events.store('index', 2)
        evl = [l for l in self.events]
        assert len(evl) == 3

    def test_getitem(self):
        self.events.store('index', 0)
        self.events.store('index', 1)
        self.events.store('index', 2)

        dl = self.events['index']
        assert len(dl) == 3
        assert _eq(dl, [0,1,2])

    def test_setitem(self):
        self.events['index'] = 0
        self.events['index'] = 1
        self.events['index'] = 2

        dl = self.events['index']
        assert len(dl) == 3
        assert _eq(dl, [0,1,2])

    def test_append(self):
        ev = Event(typ='doo', data='doo')
        self.events.append(ev)
        assert len(self.events) == 1

    def test_extend(self):
        evl = [
            Event(typ='doo', data='doo'),
            Event(typ='once', data='more'),
            Event(typ='that', data='thing'),
        ]
        self.events.extend(evl)
        assert len(self.events) == 3

    def test_last_of(self):
        self.events.store('response', HandlerResponse(True))
        self.events.store('response', HandlerResponse(True, user_action='OK'))
        self.events.store('response', Action(None))
        self.events.store('index', 0)
        self.events.store('index', 1)
        self.events.store('song', 'doremi')

        data = self.events.last_of(['response'])
        assert isinstance(data, Action)

        data = self.events.last_of(['response', 'song'])
        assert data == 'doremi'