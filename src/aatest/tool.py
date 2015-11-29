import logging
from saml2test import profiles

from aatest import exception_trace
from aatest import END_TAG
from aatest.conversation import Conversation
from aatest.verify import Verify
from aatest.session import Done

__author__ = 'roland'

logger = logging.getLogger(__name__)


def get_redirect_uris(cinfo):
    try:
        return cinfo["client"]["redirect_uris"]
    except KeyError:
        return cinfo["registered"]["redirect_uris"]


class ConfigurationError(Exception):
    pass


class Tester(object):
    def __init__(self, io, sh, profile, flows, check_factory,
                 msg_factory, cache, make_client, map_prof,
                 trace_cls, **kwargs):
        self.io = io
        self.sh = sh
        self.conv = None
        self.profile = profile
        self.flows = flows
        self.message_factory = msg_factory
        self.chk_factory = check_factory
        self.cache = cache
        self.kwargs = kwargs
        self.make_client = make_client
        self.map_prof = map_prof
        self.trace_cls = trace_cls
        self.cjar = {}

    def match_profile(self, test_id):
        _spec = self.flows[test_id]
        return self.map_prof(self.profile.split("."),
                             _spec["profile"].split("."))

    def setup(self, test_id, cinfo, **kw_args):
        if not self.match_profile(test_id):
            return False

        redirs = get_redirect_uris(cinfo)

        self.sh.session_setup(path=test_id)
        _flow = self.flows[test_id]
        _cli = self.make_client(**kw_args)
        self.conv = Conversation(_flow, _cli, redirs, kw_args["msg_factory"],
                                 trace_cls=self.trace_cls)
        _cli.conv = self.conv
        self.conv.sequence = self.sh.session["sequence"]
        self.sh.session["conv"] = self.conv
        return True
        
    def run(self, test_id, cinfo, **kw_args):
        if not self.setup(test_id, cinfo, **kw_args):
            raise ConfigurationError()

        # noinspection PyTypeChecker
        try:
            return self.run_flow(test_id, kw_args["conf"])
        except Exception as err:
            exception_trace("", err, logger)
            self.io.dump_log(self.sh.session, test_id)
            return self.io.err_response(self.sh.session, "run", err)

    def handle_response(self, resp, index):
        return None

    def run_flow(self, test_id, index=0):
        logger.info("<=<=<=<=< %s >=>=>=>=>" % test_id)
        _ss = self.sh.session
        try:
            _ss["node"].complete = False
        except KeyError:
            pass

        self.conv.test_id = test_id

        if index >= len(self.conv.sequence):
            return None

        _oper = None
        for item in self.conv.sequence[index:]:
            if isinstance(item, tuple):
                cls, funcs = item
            else:
                cls = item
                funcs = {}

            logger.info("<--<-- {} --- {} -->-->".format(index, cls))
            self.conv.events.store('operation', cls)
            try:
                _oper = cls(conv=self.conv, io=self.io, sh=self.sh,
                            profile=self.profile, test_id=test_id,
                            funcs=funcs, check_factory=self.chk_factory,
                            cache=self.cache)
                # self.conv.operation = _oper
                _oper.setup(profiles.PROFILEMAP)
                resp = _oper()
            except Exception as err:
                self.sh.session["index"] = index
                return self.io.err_response(self.sh.session, "run_sequence",
                                            err)
            else:
                resp = self.handle_response(resp, index)
                if resp:
                    return self.io.respond(resp)

            index += 1

        try:
            if self.conv.flow["tests"]:
                _ver = Verify(self.chk_factory, self.conv.msg_factory,
                              self.conv)
                _ver.test_sequence(self.conv.flow["tests"])
        except KeyError:
            pass
        except Exception as err:
            logger.error(err)
            raise

        if isinstance(_oper, Done):
            self.conv.events.store('test_output', ("X", END_TAG))
        return True
