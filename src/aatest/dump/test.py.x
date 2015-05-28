#!/usr/bin/env python
import copy
import logging

from jwkest.jws import alg2keytype

from oic.oic.message import AccessTokenResponse
from oic.oic.message import factory as message_factory
from oic.oic.message import OpenIDSchema
from oic.utils.http_util import Response
from oic.utils.http_util import Redirect

from oictest import ConfigurationError

from oictest.base import Conversation
from oictest.check import get_protocol_response
from oictest.oidcrp import test_summation
from oictest.oidcrp import OIDCTestSetup
from oictest.prof_util import flows
from oictest.utils import store_test_info, pprint_json
from oictest.utils import end_tags
from oictest.utils import get_err_type
from oictest.utils import dump_log

from aatest import Trace
from rrtest import exception_trace
from rrtest import Break
from rrtest.check import ERROR
from rrtest.check import OK
from rrtest.check import WARNING

from testclass import Done
from testclass import END_TAG
from testclass import RequirementsNotMet
from testclass import Notice
from testclass import DisplayUserInfo
from testclass import DisplayIDToken

LOGGER = logging.getLogger(__name__)

INCOMPLETE = 4

TEST_RESULTS = {OK: "OK", ERROR: "ERROR", WARNING: "WARNING",
                INCOMPLETE: "INCOMPLETE"}
CRYPTSUPPORT = {"none": "n", "signing": "s", "encryption": "e"}


class NotSupported(Exception):
    pass


def setup_logging(logfile, logger):
    hdlr = logging.FileHandler(logfile)
    base_formatter = logging.Formatter(
        "%(asctime)s %(name)s:%(levelname)s %(message)s")

    hdlr.setFormatter(base_formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.DEBUG)


def get_test_info(session, test_id):
    return session["test_info"][test_id]


def evaluate(session):
    try:
        if session["node"].complete:
            _info = session["test_info"][session["testid"]]
            if end_tags(_info):
                _sum = test_summation(_info["test_output"], session["testid"])
                session["node"].state = _sum["status"]
            else:
                session["node"].state = INCOMPLETE
        else:
            session["node"].state = INCOMPLETE
    except (AttributeError, KeyError):
        pass


class TEST(object):
    def __init__(self, lookup, conf, test_flows, cache, test_profile,
                 profiles, test_class, check_factory, environ=None,
                 start_response=None):
        self.lookup = lookup
        self.conf = conf
        self.test_flows = test_flows
        self.cache = cache
        self.test_profile = test_profile
        self.profiles = profiles
        self.test_class = test_class
        self.check_factory = check_factory
        self.environ = environ
        self.start_response = start_response

    def client_init(self):
        ots = OIDCTestSetup(self.conf, self.test_flows, str(self.conf.PORT))
        client_conf = ots.config.CLIENT
        trace = Trace()
        conv = Conversation(ots.client, client_conf, trace, None,
                            message_factory, self.check_factory)
        conv.cache = self.cache
        conv.check_factory = self.check_factory
        return ots, conv

    def session_setup(self, session, path, index=0):
        logging.info("session_setup")
        _keys = session.keys()
        for key in _keys:
            if key.startswith("_"):
                continue
            elif key in ["tests", "flow_names", "response_type",
                         "test_info", "profile"]:  # don't touch !
                continue
            else:
                del session[key]

        session["testid"] = path
        session["node"] = get_node(session["tests"], path)
        sequence_info = {
            "sequence": self.profiles.get_sequence(
                path, session["profile"], self.test_flows.FLOWS,
                self.profiles.PROFILEMAP, self.test_class.PHASES),
            "mti": session["node"].mti,
            "tests": session["node"].tests}
        sequence_info["sequence"].append((Done, {}))
        session["seq_info"] = sequence_info
        session["index"] = index
        session["response_type"] = ""
        ots, conv = self.client_init()
        session["conv"] = conv
        session["ots"] = ots

        return conv, sequence_info, ots, conv.trace, index

    def log_fault(self, session, err, where, err_type=0):
        if err_type == 0:
            err_type = get_err_type(session)

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
                if isinstance(err, basestring):
                    pass
                else:
                    session["conv"].trace.error("%s:%s" % (
                        err.__class__.__name__, str(err)))
                session["conv"].test_output.append(
                    {"id": "-", "status": err_type, "message": "%s" % err})
            else:
                session["conv"].test_output.append(
                    {"id": "-", "status": err_type,
                     "message": "Error in %s" % where})

    def err_response(self, session, where, err):
        if err:
            exception_trace(where, err, LOGGER)

        self.log_fault(session, err, where)

        try:
            _tid = session["testid"]
            dump_log(session, _tid)
            store_test_info(session)
        except KeyError:
            pass

        return self.flow_list(session)

    def sorry_response(self, homepage, err):
        resp = Response(mako_template="sorry.mako",
                        template_lookup=self.lookup,
                        headers=[])
        argv = {"htmlpage": homepage,
                "error": str(err)}
        return resp(self.environ, self.start_response, **argv)

    def none_request_response(self, sequence_info, index, session, conv):
        req_c, arg = sequence_info["sequence"][index]
        req = req_c()
        if isinstance(req, Notice):
            kwargs = {
                "url": "%scontinue?path=%s&index=%d" % (
                    self.conf.BASE, session["testid"], session["index"]),
                "back": self.conf.BASE}
            try:
                kwargs["url"] += "&ckey=%s" % session["ckey"]
            except KeyError:
                pass
            try:
                kwargs["note"] = session["node"].kwargs["note"]
            except KeyError:
                pass
            try:
                kwargs["op"] = conv.client.provider_info["issuer"]
            except (KeyError, TypeError):
                pass

            if isinstance(req, DisplayUserInfo):
                for presp, _ in conv.protocol_response:
                    if isinstance(presp, OpenIDSchema):
                        kwargs["table"] = presp
                        break
            elif isinstance(req, DisplayIDToken):
                instance, _ = get_protocol_response(
                    conv, AccessTokenResponse)[0]
                kwargs["table"] = instance["id_token"]
            else:
                kwargs["table"] = {}

            try:
                key = req.cache(self.cache, conv, sequence_info["cache"])
            except KeyError:
                pass
            else:
                kwargs["url"] += "&key=%s" % key

            return req(self.lookup, self.environ, self.start_response, **kwargs)
        else:
            try:
                return req(conv)
            except RequirementsNotMet as err:
                return self.err_response(session, "run_sequence", err)

    def init_session(self, session, profile=None):
        if profile is None:
            profile = self.test_profile

        f_names = self.test_flows.FLOWS.keys()
        f_names.sort()
        session["flow_names"] = []
        for k in self.test_flows.ORDDESC:
            k += '-'
            l = [z for z in f_names if z.startswith(k)]
            session["flow_names"].extend(l)

        session["tests"] = [make_node(x, self.test_flows.FLOWS[x]) for x in
                            flows(profile, session["flow_names"],
                                  self.test_flows.FLOWS)]

        session["response_type"] = []
        session["test_info"] = {}
        session["profile"] = profile
        if "conv" not in session:
            session["ots"], session["conv"] = self.client_init()

    def reset_session(self, session, profile=None):
        _keys = session.keys()
        for key in _keys:
            if key.startswith("_"):
                continue
            else:
                del session[key]
        self.init_session(session, profile)
        conv, ots = self.client_init()
        session["conv"] = conv
        session["ots"] = ots

    def session_init(self, session):
        if "tests" not in session:
            self.init_session(session)
            return True
        else:
            return False

    def fini(self, session, conv):
        _tid = session["testid"]
        conv.test_output.append(("X", END_TAG))
        store_test_info(session)
        dump_log(session, _tid)
        session["node"].complete = True

        _grp = _tid.split("-")[1]

        resp = Redirect("%sopresult#%s" % (self.conf.BASE, _grp))
        return resp(self.environ, self.start_response)


# =============================================================================


def get_id_token(client, conv):
    return client.grant[conv.AuthorizationRequest["state"]].get_id_token()


# Produce a JWS, a signed JWT, containing a previously received ID token
def id_token_as_signed_jwt(client, id_token, alg="RS256"):
    ckey = client.keyjar.get_signing_key(alg2keytype(alg), "")
    _signed_jwt = id_token.to_jwt(key=ckey, algorithm=alg)
    return _signed_jwt


def add_test_result(conv, status, message, tid="-"):
    conv.test_output.append({"id": str(tid),
                             "status": status,
                             "message": message})


def clear_session(session):
    for key in session:
        session.pop(key, None)
    session.invalidate()


def post_tests(conv, req_c, resp_c):
    try:
        inst = req_c(conv)
        _tests = inst.tests["post"]
    except KeyError:
        pass
    else:
        if _tests:
            conv.test_output.append((req_c.request, "post"))
            conv.test_sequence(_tests)

    if resp_c:
        try:
            inst = resp_c()
            _tests = inst.tests["post"]
        except KeyError:
            pass
        else:
            if _tests:
                conv.test_output.append((resp_c.response, "post"))
                conv.test_sequence(_tests)


DEFAULTS = {
    "response_modes_supported": ["query", "fragment"],
    "grant_types_supported": ["authorization_code", "implicit"],
    "token_endpoint_auth_methods_supported": ["client_secret_basic"],
    "claims_parameter_supported": False,
    "request_parameter_supported": False,
    "request_uri_parameter_supported": True,
    "require_request_uri_registration": False,
}


def included(val, given):
    if isinstance(val, basestring):
        assert val == given or val in given
    elif isinstance(val, list):
        for _val in val:
            assert _val == given or _val in given
    else:
        assert val == given

    return True


def not_supported(val, given):
    if isinstance(val, basestring):
        if isinstance(given, basestring):
            try:
                assert val == given
            except AssertionError:
                return [val]
        else:
            try:
                assert val in given
            except AssertionError:
                return [val]
    elif isinstance(val, list):
        if isinstance(given, basestring):
            _missing = [v for v in val if v != given]
        else:
            _missing = []
            for _val in val:
                try:
                    assert _val in given
                except AssertionError:
                    _missing.append(_val)
        if _missing:
            return _missing
    else:
        try:
            assert val == given
        except AssertionError:
            return [val]

    return None


def support(conv, args):
    pi = conv.client.provider_info
    stat = 0
    for ser in ["warning", "error"]:
        if ser not in args:
            continue
        if ser == "warning":
            err = WARNING
        else:
            err = ERROR
        for key, val in args[ser].items():
            try:
                _ns = not_supported(val, pi[key])
            except KeyError:  # Not defined
                conv.trace.info(
                    "'%s' not defined in provider configuration" % key)
            else:
                if _ns:
                    add_test_result(
                        conv, err,
                        "OP is not supporting %s according to '%s' in the provider configuration" % (val, key))
                    stat = err

    return stat


def endpoint_support(client, endpoint):
    if endpoint in client.provider_info:
        return True
    else:
        return False


def run_func(spec, conv, req_args):
    if isinstance(spec, tuple):
        func, args = spec
    else:
        func = spec
        args = {}

    try:
        req_args = func(req_args, conv, args)
    except KeyError as err:
        conv.trace.error("function: %s failed" % func)
        conv.trace.error(str(err))
        raise NotSupported
    except ConfigurationError:
        raise
    else:
        return req_args


def setup(kwa, conv):
    kwargs = copy.deepcopy(kwa)  # decouple

    # evaluate possible functions
    try:
        spec = kwargs["function"]
    except KeyError:
        pass
    else:
        kwargs["request_args"] = run_func(spec, conv, kwargs["request_args"])
        del kwargs["function"]

    try:
        spec = kwargs["kwarg_func"]
    except KeyError:
        pass
    else:
        kwargs = run_func(spec, conv, kwargs)
        del kwargs["kwarg_func"]

    try:
        res = support(conv, kwargs["support"])
        if res >= ERROR:
            raise NotSupported()

        del kwargs["support"]
    except KeyError:
        pass

    return kwargs


class Node():
    def __init__(self, name, desc="", rmc=False, experr=False, mti=None,
                 tests=None, **kwargs):
        self.name = name
        self.desc = desc
        self.state = 0
        self.rmc = rmc
        self.experr = experr
        self.mti = mti
        self.tests = tests or {}
        self.kwargs = kwargs


def make_node(x, spec):
    return Node(x, **spec)


def get_node(tests, nid):
    l = [x for x in tests if x.name == nid]
    try:
        return l[0]
    except (ValueError, IndexError):
        return None

# -----------------------------------------------------------------------------
