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
    def __init__(self, profile='', flows=None, order=None, **kwargs):
        self.profile = profile
        self.test_flows = flows
        self.order = order
        self.extra = kwargs
        self._dict = {}

    def session_setup(self, path="", index=0):
        logger.info("session_setup")

        _keys = list(self.keys())
        for key in _keys:
            if key in ["tests", "flow_names", "response_type",
                       "test_info", "profile", 'test_conf', 'sid']:
                continue
            else:
                del self[key]

        self["testid"] = path
        for node in self["tests"]:
            if node.name == path:
                self["node"] = node
                break

        self["flow"] = copy.deepcopy(self.test_flows[path])
        self["sequence"] = self["flow"]["sequence"]
        self["sequence"].append(Done)
        self["index"] = index

    def init_session(self, profile=None):
        _flows = sort(self.order, self.test_flows)
        self["flow_names"] = [f.name for f in _flows]

        _tests =[]
        for k in self["flow_names"]:
            try:
                kwargs = {"mti": self.test_flows[k]["mti"]}
            except KeyError:
                kwargs = {}
            _tests.append(Node(k, self.test_flows[k]["desc"], **kwargs))

        self["tests"] = _tests
        self["test_info"] = {}
        self["profile"] = profile or self.profile
        return self._dict

    def reset_session(self, profile=None):
        _keys = list(self.keys())
        for key in _keys:
            if key.startswith("_"):
                continue
            else:
                del self[key]
        self.init_session(profile)

    def session_init(self):
        if "tests" not in self:
            self.init_session()
            return True
        else:
            return False

    def dump(self, filename):
        pass

    def load(self, filename):
        pass

    def keys(self):
        return self._dict.keys()

    def update(self, new):
        self._dict.update(new)

    def __delitem__(self, item):
        del self._dict[item]

    def __getitem__(self, item):
        return self._dict[item]

    def __setitem__(self, key, value):
        self._dict[key] = value

    def __contains__(self, item):
        return item in self._dict

    def items(self):
        return self._dict.items()
