import pytest
from aatest.check import State, OK
from aatest.contenthandler import HandlerResponse
from aatest.conversation import Conversation
from aatest.events import Events
from aatest.events import EV_CONDITION
from aatest.events import EV_HANDLER_RESPONSE
from aatest.events import EV_HTTP_RESPONSE
from aatest.func import cache_events, factory
from aatest.func import restore_events
from aatest.func import set_op_args
from aatest.func import set_request_args

from aatest.operation import Operation

__author__ = 'roland'


class ResponseDummy(object):
    def __init__(self, status_code, content):
        self.status_code = status_code
        self.content = content


EVENT_SEQ = [
    [EV_HANDLER_RESPONSE, HandlerResponse(True)],
    [EV_CONDITION, State('1', OK)],
    [EV_HTTP_RESPONSE, ResponseDummy(200, 'html document')]
]

class TestOICConsumer():
    @pytest.fixture(autouse=True)
    def setup_operation(self):
        conv = Conversation(None, None, None)
        conv.events = Events()
        conv.test_id = 'test 1'
        self.oper = Operation(conv, None, None)

    def test_set_request_args(self):
        kwargs = {'foo': 'bar'}
        set_request_args(self.oper, kwargs)
        assert self.oper.req_args == kwargs


    def test_set_op_args(self):
        kwargs = {'foo': 'bar'}
        set_op_args(self.oper, kwargs)
        assert self.oper.op_args == kwargs


    def test_cache_restore_events(self):
        for ev in EVENT_SEQ:
            self.oper.conv.events.store(*ev)

        cache_events(self.oper, None)

        # clear events
        self.oper.conv.events.events = []

        restore_events(self.oper, None)

        assert len(self.oper.conv.events) == 3

    def test_factory(self):
        func = factory('set_allowed_status_codes')
        func(self.oper, [301,302,307])

        assert self.oper.allowed_status_codes == [301,302,307]