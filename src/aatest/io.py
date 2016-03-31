import logging

from aatest import exception_trace, Break
from aatest.check import ERROR, State
from aatest.check import WARNING
from aatest.events import EV_CONDITION
from aatest.result import Result
from aatest.result import SIGN
from aatest.summation import eval_state
from aatest.summation import represent_result

__author__ = 'roland'

logger = logging.getLogger(__name__)


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

    def _err_response(self, where, err):
        if err:
            exception_trace(where, err, logger)

        try:
            res = Result(self.session, self.profile_handler)
            res.print_info(self.session["testid"])
            res.store_test_info()
        except KeyError:
            pass

    def err_response(self, where, err):
        self._err_response(where, err)

    @staticmethod
    def get_err_type(session):
        errt = WARNING
        try:
            if session["node"].mti == {"all": "MUST"}:
                errt = ERROR
        except KeyError:
            pass
        return errt

    def log_fault(self, session, err, where, err_type=0):
        if err_type == 0:
            err_type = self.get_err_type(session)

        if "node" in session:
            if err:
                if isinstance(err, Break):
                    session["node"].state = WARNING
                else:
                    session["node"].state = err_type
            else:
                session["node"].state = err_type

        if "conv" in session:
            if err:
                if isinstance(err, str):
                    pass
                else:
                    session["conv"].trace.error("%s:%s" % (
                        err.__class__.__name__, str(err)))
                session["conv"].events.store(EV_CONDITION,
                                             State("Fault", status=ERROR,
                                                   name=err_type,
                                                   message="{}".format(err)))
            else:
                session["conv"].events.store(
                    EV_CONDITION, State(
                        "Fault", status=ERROR,
                        name=err_type,
                        message="Error in %s" % where))


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


