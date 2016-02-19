import logging
import sys
import traceback

from aatest import Break
from aatest import exception_trace
from aatest import FatalError
from aatest.check import STATUSCODE
from aatest.events import EV_CONDITION

__author__ = 'roland'

logger = logging.getLogger(__name__)

LABELS = {
    'cid': 'WHERE', 'status': 'STATUS',
    'http_status': 'HTTP STATUS', 'message': 'INFO'
}


class MissingTest(Exception):
    pass


class Verify(object):
    def __init__(self, check_factory, conv, cls_name=''):
        self.check_factory = check_factory
        self.trace = conv.trace
        self.ignore_check = []
        self.exception = None
        self.conv = conv
        self.cls_name = cls_name

    def check_severity(self, stat):
        if stat.status >= 4:
            for attr, label in LABELS.items():
                try:
                    _val = getattr(stat, attr)
                except AttributeError:
                    pass
                else:
                    if _val:
                        self.trace.error("{label}: {val}".format(val=_val,
                                                                 label=label))

            try:
                if not stat.mti:
                    raise Break(stat.message)
                else:
                    raise FatalError(stat.message)
            except KeyError:
                pass

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
                if self.cls_name:
                    stat.context = self.cls_name
                self.conv.events.store('condition', stat, sender=self.__class__)
                self.check_severity(stat)

    def err_check(self, test, err=None, bryt=True):
        if err:
            self.exception = err
        chk = self.check_factory(test)()
        chk(self, self.conv.events.last_item(EV_CONDITION))
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
        return True
