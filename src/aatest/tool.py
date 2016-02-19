import logging
from saml2.httputil import Response
from aatest.check import OK
from aatest.check import State

from aatest import exception_trace
from aatest.conversation import Conversation
from aatest.events import EV_CONDITION
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
    def __init__(self, inut, sh, profile, flows, check_factory,
                 msg_factory, cache, make_entity, map_prof,
                 trace_cls, com_handler, **kwargs):
        self.inut = inut
        self.sh = sh
        self.conv = None
        self.profile = profile
        self.flows = flows
        self.message_factory = msg_factory
        self.chk_factory = check_factory
        self.cache = cache
        self.kwargs = kwargs
        self.make_entity = make_entity
        self.map_prof = map_prof
        self.trace_cls = trace_cls
        self.com_handler = com_handler
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
        _cli = self.make_entity(**kw_args)
        self.conv = Conversation(_flow, _cli, redirs, kw_args["msg_factory"],
                                 trace_cls=self.trace_cls)
        _cli.conv = self.conv
        self.com_handler.conv = self.conv
        self.conv.sequence = self.sh.session["sequence"]
        self.sh.session["conv"] = self.conv
        return True

    def run(self, test_id, **kw_args):
        if not self.setup(test_id, **kw_args):
            raise ConfigurationError()

        # noinspection PyTypeChecker
        try:
            return self.run_flow(test_id)
        except Exception as err:
            exception_trace("", err, logger)
            self.inut.print_info(self.sh.session, test_id)
            return self.inut.err_response(self.sh.session, "run", err)

    def handle_response(self, resp, index, oper=None):
        return None

    def run_flow(self, test_id, index=0, profiles=None):
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
            self.conv.events.store('operation', cls, sender='run_flow')
            try:
                _oper = cls(conv=self.conv, inut=self.inut, sh=self.sh,
                            profile=self.profile, test_id=test_id,
                            funcs=funcs, check_factory=self.chk_factory,
                            cache=self.cache)
                # self.conv.operation = _oper
                if profiles:
                    profile_map = profiles.PROFILEMAP
                else:
                    profile_map = None
                _oper.setup(profile_map)
                resp = _oper()
            except Exception as err:
                exception_trace('run_flow', err)
                self.sh.session["index"] = index
                return self.inut.err_response(self.sh.session, "run_sequence",
                                              err)
            else:
                if isinstance(resp, Response):
                    return resp

                if resp:
                    if self.com_handler:
                        resp = self.com_handler(resp)
                    resp = _oper.handle_response(resp.response)
                    if resp:
                        return self.inut.respond(resp)

            index += 1

        try:
            if self.conv.flow["assert"]:
                _ver = Verify(self.chk_factory, self.conv)
                _ver.test_sequence(self.conv.flow["assert"])
        except KeyError:
            pass
        except Exception as err:
            logger.error(err)
            raise

        if isinstance(_oper, Done):
            self.conv.events.store(EV_CONDITION, State('Done', OK),
                                   sender='run_flow')
        return True
