from aatest.check import State, OK
from aatest.contenthandler import HandlerResponse
from aatest.conversation import Conversation
from aatest.events import Events
from aatest.events import EV_CONDITION
from aatest.events import EV_HANDLER_RESPONSE
from aatest.events import EV_HTTP_RESPONSE
from aatest.func import cache_events
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

def test_set_request_args():
    oper = Operation(None, None, None)
    kwargs = {'foo': 'bar'}
    set_request_args(oper, kwargs)
    assert oper.req_args == kwargs


def test_set_op_args():
    oper = Operation(None, None, None)
    kwargs = {'foo': 'bar'}
    set_op_args(oper, kwargs)
    assert oper.op_args == kwargs


def test_cache_restore_events():
    conv = Conversation(None, None, None)
    conv.events = Events()
    conv.test_id = 'test 1'
    oper = Operation(conv, None, None)

    for ev in EVENT_SEQ:
        conv.events.store(*ev)

    cache_events(oper, None)

    # clear events
    conv.events.events = []

    restore_events(oper, None)

    assert len(conv.events) == 3