import logging
import sys
import traceback

from aatest import Break, exception_trace
from aatest import FatalError
from aatest.check import STATUSCODE
from aatest.check import ExpectedError
from aatest.events import NoSuchEvent

__author__ = 'roland'

logger = logging.getLogger(__name__)


class MissingTest(Exception):
    pass


class Verify(object):
    def __init__(self, check_factory, msg_factory, conv):
        self.check_factory = check_factory
        self.msg_factory = msg_factory
        self.trace = conv.trace
        self.ignore_check = []
        self.exception = None
        self.conv = conv

    def check_severity(self, stat):
        #if isinstance(stat, TestResult):
        if stat.status >= 4:
            try:
                self.trace.error("WHERE: {}".format(stat.cid))
            except AttributeError:
                pass
            self.trace.error("STATUS: {}".format(STATUSCODE[stat.status]))
            try:
                self.trace.error("HTTP STATUS: {}".format(stat.http_status))
            except AttributeError:
                pass
            try:
                self.trace.error("INFO: {}".format(stat.message))
            except KeyError:
                pass

            try:
                if not stat.mti:
                    raise Break(stat.message)
                else:
                    raise FatalError(stat.message)
            except KeyError:
                pass
        # elif stat['status'] >= 4:
        #     self.trace.error("WHERE: {}".format(stat['cid']))
        #     self.trace.error("STATUS: {}".format(STATUSCODE[stat['status']]))
        #     try:
        #         self.trace.error("HTTP STATUS: {}".format(stat['http_status']))
        #     except KeyError:
        #         pass
        #     try:
        #         self.trace.error("INFO: {}".format(stat['message']))
        #     except KeyError:
        #         pass
        #
        #     try:
        #         if not stat['mti']:
        #             raise Break(stat['message'])
        #         else:
        #             raise FatalError(stat['message'])
        #     except KeyError:
        #         pass

    def do_check(self, test, **kwargs):
        logger.debug("do_check({}, {})".format(test, kwargs))
        if isinstance(test, str):
            try:
                chk = self.check_factory(test)(**kwargs)
            except TypeError:
                raise MissingTest(test)
        else:
            chk = test(**kwargs)

        if chk.__class__.__name__ not in self.ignore_check:
            self.conv.trace.info("Assert {}".format(chk.__class__.__name__))
            try:
                stat = chk(self.conv)
            except Exception as err:
                exception_trace('do_check', err, logger)
                raise
            else:
                self.conv.events.store('condition', stat)
                self.check_severity(stat)

    def err_check(self, test, err=None, bryt=True):
        if err:
            self.exception = err
        chk = self.check_factory(test)()
        chk(self, self.conv.events.last_item('condition'))
        if bryt:
            e = FatalError("%s" % err)
            e.trace = "".join(traceback.format_exception(*sys.exc_info()))
            raise e

    def test_sequence(self, sequence):
        if isinstance(sequence, dict):
            for test, kwargs in list(sequence.items()):
                if not kwargs:
                    self.do_check(test)
                else:
                    self.do_check(test, **kwargs)
        else:
            for test in sequence:
                if isinstance(test, tuple):
                    test, kwargs = test
                    if not kwargs:
                        kwargs = {}
                else:
                    kwargs = {}
                self.do_check(test, **kwargs)
                if test == ExpectedError:
                    return False
        return True
