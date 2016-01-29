import logging
from saml2.time_util import in_a_while
from aatest import exception_trace

from aatest.check import ERROR
from aatest.check import OK
from aatest.check import WARNING
from aatest.check import INCOMPLETE
from aatest.summation import condition
from aatest.summation import eval_state
from aatest.summation import represent_result
from aatest.summation import trace_output

__author__ = 'roland'

logger = logging.getLogger(__name__)

TEST_RESULTS = {OK: "OK", ERROR: "ERROR", WARNING: "WARNING",
                INCOMPLETE: "INCOMPLETE"}


class IO(object):
    def __init__(self, flows, profile, check_factory, desc='',
                 profile_handler=None,
                 cache=None, **kwargs):
        self.flows = flows
        self.cache = cache
        self.test_profile = profile
        self.profile_handler = profile_handler
        self.check_factory = check_factory
        self.desc = desc

    def dump_log(self, session, test_id):
        pass

    def err_response(self, session, where, err):
        pass


SIGN = {OK: "+", WARNING: "?", ERROR: "-", INCOMPLETE: "!"}


class ClIO(IO):
    def flow_list(self, session):
        pass

    @staticmethod
    def represent_result(events):
        return represent_result(events)

    def dump_log(self, session, test_id):
        try:
            _conv = session["conv"]
        except KeyError:
            pass
        else:
            sline = 60 * "="
            _pi = None

            if self.profile_handler:
                try:
                    _pi = self.profile_handler(session).get_profile_info(test_id)
                except Exception as err:
                    raise

            if _pi:
                output = ["%s: %s" % (k, _pi[k]) for k in ["Issuer", "Profile",
                                                           "Test ID"]]
            else:
                output = ['Test ID: {}'.format(_conv.test_id)]

            output.append("Timestamp: {}".format(in_a_while()))
            output.extend(["", sline, ""])
            output.extend(trace_output(_conv.trace))
            output.extend(["", sline, ""])
            output.extend(condition(_conv.events))
            output.extend(["", sline, ""])
            # and lastly the result
            info = {
                "events": _conv.events,
                "trace": _conv.trace
            }
            output.append(
                "RESULT: {}".format(self.represent_result(_conv.events)))
            output.append("")

            txt = "\n".join(output)

            print(txt)

    @staticmethod
    def result(session):
        _state = eval_state(session["conv"].events)
        print(("{} {}".format(SIGN[_state], session["node"].name)))

    def err_response(self, session, where, err):
        if err:
            exception_trace(where, err, logger)

        try:
            _tid = session["testid"]
            self.dump_log(session, _tid)
        except KeyError:
            pass
