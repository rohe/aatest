import logging
from saml2.time_util import in_a_while
from aatest import exception_trace

from aatest.check import ERROR
from aatest.check import OK
from aatest.check import WARNING
from aatest.check import INCOMPLETE
from aatest.summation import represent_result
from aatest.summation import evaluate
from aatest.summation import condition
from aatest.summation import trace_output

__author__ = 'roland'

logger = logging.getLogger(__name__)

TEST_RESULTS = {OK: "OK", ERROR: "ERROR", WARNING: "WARNING",
                INCOMPLETE: "INCOMPLETE"}


class IO(object):
    def __init__(self, flows, profile,
                 check_factory, desc, profile_handler, cache=None, **kwargs):
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
    def represent_result(info, session):
        return represent_result(info, session)

    def dump_log(self, session, test_id):
        try:
            _conv = session["conv"]
        except KeyError:
            pass
        else:
            try:
                _pi = self.profile_handler(session).get_profile_info(test_id)
            except TypeError:
                _pi = None
            except Exception as err:
                raise

            sline = 60*"="
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
                "condition": condition(_conv.events),
                "trace": _conv.trace
            }
            output.append(
                "RESULT: {}".format(self.represent_result(info, session)))
            output.append("")

            txt = "\n".join(output)

            print(txt)

    def result(self, session):
        _conv = session["conv"]
        info = {
            "conditions": _conv.events.get_data('condition'),
            "trace": _conv.trace
        }
        _state = evaluate(session, info)
        print(("{} {}".format(SIGN[_state], session["node"].name)))

    def err_response(self, session, where, err):
        if err:
            exception_trace(where, err, logger)

        try:
            _tid = session["testid"]
            self.dump_log(session, _tid)
        except KeyError:
            pass