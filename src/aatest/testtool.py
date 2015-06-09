import logging
from aatest import exception_trace

from aatest.conversation import Conversation
from aatest.summation import test_summation
from aatest.verify import Verify

__author__ = 'roland'

logger = logging.getLogger(__name__)

class Tester(object):
    def __init__(self, interface, profiles, profile, flows, chk_factory,
                 session_handler, make_client):
        self.interface = interface
        self.profiles = profiles
        self.profile = profile
        self.flows = flows
        self.sh = session_handler
        self.conv = None
        self.chk_factory = chk_factory
        self.make_client = make_client

    def run(self, test_id, cinfo, **kw_args):
        try:
            redirs = cinfo["client"]["redirect_uris"]
        except KeyError:
            redirs = cinfo["registered"]["redirect_uris"]

        _flow = self.flows[test_id]
        _cli = self.make_client(**kw_args)
        self.conv = Conversation(_flow, _cli, redirs, kw_args["msg_factory"])
        # noinspection PyTypeChecker
        try:
            self.run_flow(test_id, kw_args["conf"])
        except Exception as err:
            exception_trace("", err, logger)
            self.interface.dump_log(self.sh.session, test_id)

    def run_flow(self, test_id, conf, index=0):
        #print("=="+test_id)
        self.conv.test_id = test_id
        self.conv.conf = conf

        if index >= len(self.conv.flow["sequence"]):
            return None

        self.conv.index = index

        for item in self.conv.flow["sequence"][index:]:
            if isinstance(item, tuple):
                cls, funcs = item
            else:
                cls = item
                funcs = {}

            _oper = cls(self.conv, self.profile, test_id, conf, funcs,
                        self.chk_factory)
            self.conv.operation = _oper
            _oper.setup(self.profiles.PROFILEMAP)
            _oper()

            self.conv.index += 1

        try:
            if self.conv.flow["tests"]:
                _ver = Verify(self.chk_factory, self.conv.msg_factory,
                              self.conv)
                _ver.test_sequence(self.conv.flow["tests"])
        except KeyError:
            pass
        except Exception as err:
            raise

        info = test_summation(self.conv, test_id)

        return info