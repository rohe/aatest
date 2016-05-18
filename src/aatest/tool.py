import logging

from aatest import ConditionError
from aatest import exception_trace
from aatest.check import OK
from aatest.check import State
from aatest.conversation import Conversation
from aatest.events import EV_CONDITION, EV_FAULT
from aatest.result import Result
from aatest.session import Done
from aatest.summation import store_test_state
from aatest.verify import Verify

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
    def __init__(self, inut, sh, profile, flows=None, check_factory=None,
                 msg_factory=None, cache=None, make_entity=None, map_prof=None,
                 trace_cls=None, com_handler=None, response_cls=None, **kwargs):
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
        self.response_cls = response_cls

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
        self.conv.sequence = self.sh["sequence"]
        self.sh["conv"] = self.conv
        return True

    def run(self, test_id, **kw_args):
        if not self.setup(test_id, **kw_args):
            raise ConfigurationError()

        # noinspection PyTypeChecker
        try:
            return self.run_flow(test_id, conf=kw_args['conf'])
        except Exception as err:
            exception_trace("", err, logger)
            return self.inut.err_response("run", err)

    def handle_response(self, resp, index, oper=None):
        return None

    def fname(self, test_id):
        raise NotImplemented()

    def get_response(self, resp):
        try:
            return resp.response
        except AttributeError:
            return resp.text

    def run_flow(self, test_id, index=0, profiles=None, **kwargs):
        logger.info("<=<=<=<=< %s >=>=>=>=>" % test_id)
        _ss = self.sh
        try:
            _ss["node"].complete = False
        except KeyError:
            pass

        self.conv.test_id = test_id
        res = Result(self.sh, self.kwargs['profile_handler'])

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
            except ConditionError:
                store_test_state(self.sh, self.conv.events)
                res.store_test_info()
                res.print_info(test_id, self.fname(test_id))
                return False
            except Exception as err:
                exception_trace('run_flow', err)
                self.conv.events.store(EV_FAULT, err)
                self.sh["index"] = index
                return self.inut.err_response("run_sequence", err)
            else:
                if isinstance(resp, self.response_cls):
                    return resp

                if resp:
                    if self.com_handler:
                        resp = self.com_handler(resp)

                    resp = _oper.handle_response(self.get_response(resp))

                    if resp:
                        return self.inut.respond(resp)

            # should be done as late as possible, so all processing has been
            # done
            try:
                _oper.post_tests()
            except ConditionError:
                store_test_state(self.sh, self.conv.events)
                res.store_test_info()
                res.print_info(test_id, self.fname(test_id))
                return False

            index += 1

        _ss['index'] = self.conv.index = index

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
            store_test_state(self.sh, self.conv.events)
            res.store_test_info()
            res.print_info(test_id, self.fname(test_id))
        else:
            store_test_state(self.sh, self.conv.events)
            res.store_test_info()

        return True
