import logging
from saml2.time_util import in_a_while
from aatest import exception_trace

from aatest.check import ERROR
from aatest.check import OK
from aatest.check import WARNING
from aatest.check import INCOMPLETE
from aatest.summation import represent_result
from aatest.summation import evaluate
from aatest.summation import test_output
from aatest.summation import trace_output

__author__ = 'roland'

logger = logging.getLogger(__name__)

TEST_RESULTS = {OK: "OK", ERROR: "ERROR", WARNING: "WARNING",
                INCOMPLETE: "INCOMPLETE"}


class IO(object):
    def __init__(self, conf, flows, profile, profiles, operation,
                 check_factory, desc, profile_handler, cache=None, **kwargs):
        self.conf = conf
        self.flows = flows
        self.cache = cache
        self.test_profile = profile
        self.profiles = profiles
        self.operation = operation
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

    def dump_log(self, session, test_id):
        try:
            _conv = session["conv"]
        except KeyError:
            pass
        else:
            _pi = self.profile_handler(session).get_profile_info(test_id)
            if _pi:
                sline = 60*"="
                output = ["%s: %s" % (k, _pi[k]) for k in ["Issuer", "Profile",
                                                           "Test ID"]]
                output.append("Timestamp: %s" % in_a_while())
                output.extend(["", sline, ""])
                output.extend(trace_output(_conv.trace))
                output.extend(["", sline, ""])
                output.extend(test_output(_conv.test_output))
                output.extend(["", sline, ""])
                # and lastly the result
                info = {
                    "test_output": _conv.test_output,
                    "trace": _conv.trace
                }
                output.append("RESULT: %s" % represent_result(info, session))
                output.append("")

                txt = "\n".join(output)

                print(txt)

    def result(self, session):
        _conv = session["conv"]
        info = {
            "test_output": _conv.test_output,
            "trace": _conv.trace
        }
        _state = evaluate(session, info)
        print "{} {}".format(SIGN[_state], session["node"].name)

    def err_response(self, session, where, err):
        if err:
            exception_trace(where, err, logger)

        try:
            _tid = session["testid"]
            self.dump_log(session, _tid)
        except KeyError:
            pass