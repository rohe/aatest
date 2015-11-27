import sys
import traceback

from aatest import Break
from aatest import FatalError
from aatest.check import STATUSCODE
from aatest.check import ExpectedError

__author__ = 'roland'


class Verify(object):
    def __init__(self, check_factory, msg_factory, conv):
        self.check_factory = check_factory
        self.msg_factory = msg_factory
        self.trace = conv.trace
        self.ignore_check = []
        self.exception = None
        self.conv = conv

    def check_severity(self, stat):
        if stat["status"] >= 4:
            self.trace.error("WHERE: %s" % stat["id"])
            self.trace.error("STATUS:%s" % STATUSCODE[stat["status"]])
            try:
                self.trace.error("HTTP STATUS: %s" % stat["http_status"])
            except KeyError:
                pass
            try:
                self.trace.error("INFO: %s" % (stat["message"],))
            except KeyError:
                pass

            if not stat["mti"]:
                raise Break(stat["message"])
            else:
                raise FatalError(stat["message"])

    def do_check(self, test, **kwargs):
        if isinstance(test, str):
            chk = self.check_factory(test)(**kwargs)
        else:
            chk = test(**kwargs)

        if chk.__class__.__name__ not in self.ignore_check:
            try:
                output = self.conv.events.last('test_output').data
            except AttributeError:
                output = None

            stat = chk(self.conv, output)
            if stat:
                self.check_severity(stat)

    def err_check(self, test, err=None, bryt=True):
        if err:
            self.exception = err
        chk = self.check_factory(test)()
        chk(self, self.conv.events.last('test_output').data)
        if bryt:
            e = FatalError("%s" % err)
            e.trace = "".join(traceback.format_exception(*sys.exc_info()))
            raise e

    def test_sequence(self, sequence):
        if isinstance(sequence, dict):
            for test, kwargs in list(sequence.items()):
                self.do_check(test, **kwargs)
        else:
            for test in sequence:
                if isinstance(test, tuple):
                    test, kwargs = test
                else:
                    kwargs = {}
                self.do_check(test, **kwargs)
                if test == ExpectedError:
                    return False
        return True
