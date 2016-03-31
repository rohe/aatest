import os

from future.backports.urllib.parse import quote

from aatest.check import ERROR
from aatest.check import OK
from aatest.check import WARNING
from aatest.check import INCOMPLETE
from aatest.summation import condition
from aatest.summation import represent_result
from aatest.summation import trace_output
from aatest.summation import eval_state
from aatest.time_util import in_a_while


SIGN = {OK: "+", WARNING: "!", ERROR: "-", INCOMPLETE: "?"}
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


class Result(object):
    def __init__(self, session, profile_handler):
        self.profile_handler = profile_handler
        self.session = session

    def result(self):
        _state = eval_state(self.session["conv"].events)
        print("{} {}".format(SIGN[_state], self.session["node"].name))

    def print_result(self, events):
        return represent_result(events)

    def _profile_info(self, test_id):
        if self.profile_handler:
            ph = self.profile_handler(self.session)
            try:
                return ph.get_profile_info(test_id)
            except Exception as err:
                raise
        return {}

    def print_info(self, test_id, filename=''):
        if 'conv' not in self.session:
            return
        else:
            _conv = self.session["conv"]

        sline = 60 * "="

        _pi = self._profile_info(test_id)

        if _pi:
            _keys = list(_pi.keys())
            _keys.sort()
            output = ["%s: %s" % (k, _pi[k]) for k in _keys]
        else:
            output = ['Test ID: {}'.format(_conv.test_id),
                      "Timestamp: {}".format(in_a_while())]

        output.extend(["", sline, ""])
        output.extend(trace_output(_conv.trace))
        output.extend(["", sline, ""])
        output.extend(condition(_conv.events))
        output.extend(["", sline, ""])
        output.extend(['Events', '{}'.format(_conv.events)])
        output.extend(["", sline, ""])
        # and lastly the result
        output.append(
            "RESULT: {}".format(self.print_result(_conv.events)))
        output.append("")

        txt = "\n".join(output)

        if filename:
            f = open(filename, 'w')
            f.write(txt)
            f.close()
        else:
            print(txt)

    def store_test_info(self, profile_info=None):
        _info = {
            "descr": self.session["node"].desc,
            "events": self.session["conv"].events,
            "index": self.session["index"],
            #"seqlen": len(self.session["seq_info"]["sequence"]),
            "test_output": self.session["conv"].events.get('condition'),
            "trace": self.session["conv"].trace,
        }

        try:
            _info["node"] = self.session["seq_info"]["node"]
        except KeyError:
            pass

        if profile_info:
            _info["profile_info"] = profile_info
        else:
            _info['profile_info'] = self._profile_info(self.session["testid"])

        self.session["test_info"][self.session["testid"]] = _info
