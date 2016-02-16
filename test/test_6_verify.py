from aatest import Trace, FatalError
from aatest.check import factory as check_factory
from aatest.check import OK
from aatest.check import CRITICAL
from aatest.conversation import Conversation
from aatest.events import Events
from aatest.events import EV_CONDITION
from aatest.events import EV_HTTP_RESPONSE
from aatest.verify import Verify
import pytest

__author__ = 'roland'


class ResponseDummy(object):
    def __init__(self, status_code):
        self.status_code = status_code


class TestVerify(object):
    @pytest.fixture(autouse=True)
    def create_vi(self):
        self.conv = Conversation(None, None, None)
        self.conv.events = Events()
        self.conv.trace = Trace()
        self.verify = Verify(check_factory, self.conv)

    def test_1(self):
        self.conv.events.store(EV_HTTP_RESPONSE, ResponseDummy(200))
        tests = {'http_response': None}
        res = self.verify.test_sequence(tests)
        assert res
        assert len(self.conv.events) == 2
        ev = self.conv.events[EV_CONDITION]
        assert len(ev) == 1
        assert ev[0].status == OK

    def test_2(self):
        self.conv.events.store(EV_HTTP_RESPONSE, ResponseDummy(500))
        tests = {'http_response': None}
        try:
            _ = self.verify.test_sequence(tests)
        except FatalError:
            pass

        assert len(self.conv.events) == 2
        ev = self.conv.events[EV_CONDITION]
        assert len(ev) == 1
        assert ev[0].status == CRITICAL

    def test_3(self):
        self.conv.events.store(EV_HTTP_RESPONSE, ResponseDummy(303))
        tests = [('http_response', {})]
        res = self.verify.test_sequence(tests)
        assert res
        assert len(self.conv.events) == 2
        ev = self.conv.events[EV_CONDITION]
        assert len(ev) == 1
        assert ev[0].status == OK

    def test_4(self):
        self.conv.events.store(EV_HTTP_RESPONSE, ResponseDummy(303))
        tests = ['http_response']
        res = self.verify.test_sequence(tests)
        assert res
        assert len(self.conv.events) == 2
        ev = self.conv.events[EV_CONDITION]
        assert len(ev) == 1
        assert ev[0].status == OK
