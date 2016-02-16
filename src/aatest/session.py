import copy
import logging
from aatest.parse_cnf import sort
from aatest import END_TAG
from aatest.operation import Operation

__author__ = 'roland'

logger = logging.getLogger(__name__)


class Done(Operation):
    def run(self, *args, **kwargs):
        self.conv.trace.info(END_TAG)


class Node(object):
    def __init__(self, name, desc, mti=None):
        self.name = name
        self.desc = desc
        self.mti = mti
        self.state = 0
        self.info = ""
        self.rmc = False
        self.experr = False
        self.complete = False


class SessionHandler(object):
    def __init__(self, session, profile='', flows=None, order=None,
                 **kwargs):
        self.session = session or {}
        self.profile = profile
        self.test_flows = flows
        self.order = order
        self.extra = kwargs

    def session_setup(self, session=None, path="", index=0):
        logger.info("session_setup")
        if session is None:
            session = self.session
        _keys = list(session.keys())
        for key in _keys:
            if key.startswith("_"):
                continue
            elif key in ["tests", "flow_names", "response_type",
                         "test_info", "profile"]:  # don't touch !
                continue
            else:
                del session[key]

        session["testid"] = path
        for node in session["tests"]:
            if node.name == path:
                session["node"] = node
                break

        session["flow"] = copy.deepcopy(self.test_flows[path])
        session["sequence"] = session["flow"]["sequence"]
        session["sequence"].append(Done)
        session["index"] = index
        self.session = session

    def init_session(self, session, profile=None):
        if profile is None:
            profile = self.profile

        _flows = sort(self.order, self.test_flows)
        session["flow_names"] = [f.name for f in _flows]

        _tests =[]
        for k in session["flow_names"]:
            try:
                kwargs = {"mti": self.test_flows[k]["mti"]}
            except KeyError:
                kwargs = {}
            _tests.append(Node(k, self.test_flows[k]["desc"], **kwargs))

        session["tests"] = _tests
        session["test_info"] = {}
        session["profile"] = profile
        self.session = session
        return session

    def reset_session(self, session=None, profile=None):
        if not session:
            session = self.session

        _keys = list(session.keys())
        for key in _keys:
            if key.startswith("_"):
                continue
            else:
                del session[key]
        self.init_session(session, profile)

    def session_init(self, session=None):
        if not session:
            session = self.session

        if "tests" not in session:
            self.init_session(session)
            return True
        else:
            return False
