import logging
import os
from future.backports.urllib.parse import quote

try:
    from saml2.time_util import in_a_while
except ImportError:
    from oic.utils.time_util import in_a_while

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


def safe_path(eid, *args):
    s = quote(eid)
    s = s.replace('/', '%2F')

    path = 'log/{}'.format(s)
    for arg in args[:-1]:
        path = '{}/{}'.format(path, arg)

    if not os.path.isdir(path):
        os.makedirs(path)

    return '{}/{}'.format(path, args[-1])


class IO(object):
    def __init__(self, flows, profile, desc='', profile_handler=None,
                 cache=None, session=None, **kwargs):
        self.flows = flows
        self.cache = cache
        self.test_profile = profile
        self.profile_handler = profile_handler
        self.desc = desc
        self.session = session

    def represent_result(self, events):
        return represent_result(events)

    def print_info(self, test_id, filename=''):
        if 'conv' not in self.session:
            return
        else:
            _conv = self.session["conv"]

        sline = 60 * "="
        _pi = None

        if self.profile_handler:
            ph = self.profile_handler(self.session)
            try:
                _pi = ph.get_profile_info(test_id)
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
        output.extend(['Events', '{}'.format(_conv.events)])
        output.extend(["", sline, ""])
        # and lastly the result
        output.append(
            "RESULT: {}".format(self.represent_result(_conv.events)))
        output.append("")

        txt = "\n".join(output)

        if filename:
            f = open(filename, 'w')
            f.write(txt)
            f.close()
        else:
            print(txt)

    def err_response(self, where, err):
        pass


SIGN = {OK: "+", WARNING: "?", ERROR: "-", INCOMPLETE: "!"}


class ClIO(IO):
    def __init__(self, flows, profile, desc='', profile_handler=None,
                 cache=None, session=None, **kwargs):
        IO.__init__(self, flows, profile, desc, profile_handler, cache,
                    session=session, **kwargs)

    def flow_list(self):
        pass

    def result(self):
        _state = eval_state(self.session["conv"].events)
        print(("{} {}".format(SIGN[_state], self.session["node"].name)))

    def err_response(self, where, err):
        if err:
            exception_trace(where, err, logger)

        try:
            _tid = self.session["testid"]
            self.print_info(self.session, _tid)
        except KeyError:
            pass

