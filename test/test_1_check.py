from aatest.check import assert_summation
from aatest.check import Check
from aatest.check import CheckHTTPResponse
from aatest.check import CRITICAL
from aatest.check import OK
from aatest.check import State
from aatest.check import WARNING
from aatest.conversation import Conversation
from aatest.events import Events, EV_HTTP_RESPONSE
from aatest.events import EV_CONDITION

__author__ = 'roland'


def test_init_state():
    state = State('test_id', OK)
    assert state.test_id == 'test_id'
    assert state.status == OK

    s = str(state)
    assert s == 'test_id: status=OK'


def test_init_state_with_name():
    state = State('test_id', OK, name='name')

    s = str(state)
    assert s == 'test_id: status=OK [name]'


def test_init_state_with_message():
    state = State('test_id', WARNING, message='msg')

    s = str(state)
    assert s == 'test_id: status=WARNING, message=msg'


def test_init_state_with_context():
    state = State('test_id', OK, context='ctx')

    s = str(state)
    assert s == 'ctx:test_id: status=OK'


def test_test_summation():
    events = Events()
    events.store(EV_CONDITION, State('1', OK))
    events.store(EV_CONDITION, State('2', OK))
    events.store(EV_CONDITION, State('3', WARNING))

    sum = assert_summation(events, 'flow1')

    assert set(sum.keys()) == {'id', 'status', 'assertions'}
    assert sum['id'] == 'flow1'
    assert sum['status'] == WARNING


def test_check():
    chk = Check()
    s = chk()

    assert isinstance(s, State)
    assert s.status == OK
    assert s.test_id == Check.cid


class ResponseDummy(object):
    def __init__(self, status_code):
        self.status_code = status_code


def test_check_http_response_200():
    chk = CheckHTTPResponse(status_code=[200])
    conv = Conversation(None, None, None)
    conv.events = Events()
    conv.events.store(EV_HTTP_RESPONSE, ResponseDummy(200))

    state = chk(conv)
    assert state.status == OK
    assert state.test_id == 'http_response'


def test_check_http_response_unexpected_400():
    chk = CheckHTTPResponse(status_code=[200])
    conv = Conversation(None, None, None)
    conv.events = Events()
    conv.events.store(EV_HTTP_RESPONSE, ResponseDummy(400))

    state = chk(conv)
    assert state.status == CRITICAL
    assert state.test_id == 'http_response'
    assert state.message == 'Incorrect HTTP status_code'


def test_check_http_response_expected_400():
    chk = CheckHTTPResponse(status_code=[400])
    conv = Conversation(None, None, None)
    conv.events = Events()
    conv.events.store(EV_HTTP_RESPONSE, ResponseDummy(400))

    state = chk(conv)
    assert state.status == OK
    assert state.test_id == 'http_response'


def test_check_http_response_one_of():
    chk = CheckHTTPResponse(status_code=[301,302,307])
    conv = Conversation(None, None, None)
    conv.events = Events()
    conv.events.store(EV_HTTP_RESPONSE, ResponseDummy(302))

    state = chk(conv)
    assert state.status == OK
    assert state.test_id == 'http_response'
