import logging
from aatest import get_node
from aatest import make_node
from aatest import Trace

__author__ = 'roland'

logger = logging.getLogger(__name__)


class TEST(object):
    def __init__(self, test_flows, profiles, test_class, test_profile,
                 prof_util, conv_class):
        self.test_flows = test_flows,
        self.profiles = profiles
        self.profile = test_profile
        self.test_class = test_class
        self.dir = dir
        self.prof_util = prof_util
        self.tests = []
        self.testid = ""
        self.node = None
        self.flow_names = []
        self.seq_info = []
        self.index = 0
        self.response_type = ""
        self.trace = Trace()
        self.conv = conv_class()

    def gather_tests(self):
        f_names = self.test_flows.FLOWS.keys()
        f_names.sort()
        for k in self.test_flows.ORDDESC:
            k += '-'
            l = [z for z in f_names if z.startswith(k)]
            self.flow_names.extend(l)

        self.tests = [make_node(x, self.test_flows.FLOWS[x]) for x in
                      self.prof_util.flows(self.profile, self.flow_names,
                                           self.test_flows.FLOWS)]

    def get_sequence(self, testid):
        """

        :param testid:
        :return:
        """
        self.testid = testid
        self.node = get_node(self.tests, testid)
        sequence_info = {
            "sequence": self.profiles.get_sequence(
                testid, self.profile, self.test_flows.FLOWS,
                self.profiles.PROFILEMAP, self.test_class.PHASES),
            "mti": self.node.mti,
            "tests": self.node.tests}
        sequence_info["sequence"].append((self.test_class.Done, {}))
        self.seq_info = sequence_info
        self.response_type = ""

    def setup(self):
        self.conv = None
        self.ots = None

    def dump_log(self):
        raise NotImplemented

    def none_request_response(self, index):
        raise NotImplemented

    def run_sequence(self, trace, index):
        while index < len(self.seq_info["sequence"]):
            logger.info("###{i}### {f} ###{i}###".format(f=self.testid,
                                                         i=index))
            self.index = index
            try:
                (req_c, resp_c), _kwa = self.seq_info["sequence"][index]
            except (ValueError, TypeError):  # Not a tuple
                ret = self.none_request_response(index)
                self.dump_log()
                if isinstance(ret, basestring):
                    session["ckey"] = ret
                elif ret:
                    return ret
            else:
                if self.conv.protocol_response:
                    # If last response was an error response, bail out.
                    inst, txt = self.conv.protocol_response[-1]
                    try:
                        session["expect_error"]
                    except KeyError:
                        if isinstance(inst, ErrorResponse):
                            return self.err_response(session,"", inst)
                try:
                    kwargs = setup(_kwa, conv)
                except NotSupported:
                    self.store_test_info(session)
                    return self.opresult(conv, session)
                except Exception as err:
                    return self.err_response(session, "function()", err)

                try:
                    expect_error = _kwa["expect_error"]
                except KeyError:
                    expect_error = None
                else:
                    del _kwa["expect_error"]

                req = req_c(conv)
                try:
                    _pt = req.tests["pre"]
                except KeyError:
                    pass
                else:
                    if _pt:
                        try:
                            conv.test_output.append((req.request, "pre"))
                            conv.test_sequence(_pt)
                        except Exception as err:
                            return self.err_response(session, "pre-test", err)

                conv.request_spec = req

                conv.trace.info("------------ %s ------------" % req_c.request)
                if req_c == Discover:
                    # Special since it's just a GET on a URL
                    try:
                        _r = req.discover(
                            ots.client,
                            issuer=ots.config.CLIENT["srv_discovery_url"])
                    except ConnectionError:
                            self.log_fault(session, "Connection Error",
                                           "discover_request", ERROR)
                            conv.trace.info(END_TAG)
                            return self.fini(session, conv)

                    conv.position, conv.last_response, conv.last_content = _r

                    if conv.last_response.status >= 400:
                        return self.err_response(session, "discover",
                                                 conv.last_response.text)

                    for x in ots.client.keyjar[
                            ots.client.provider_info["issuer"]]:
                        try:
                            resp = ots.client.http_request(x.source)
                        except Exception as err:
                            return self.err_response(session, "jwks_fetch",
                                                     str(err))
                        else:
                            conv.last_response = resp
                            conv.last_content = resp.content
                            if resp.status_code < 300:
                                trace.info(
                                    "JWKS: %s" % pprint_json(resp.content))
                            else:
                                return self.err_response(session, "jwks_fetch",
                                                         resp.content)
                elif req_c == Webfinger:
                    try:
                        url = req.discover(**kwargs)
                    except ConnectionError:
                            self.log_fault(session, "Connection Error",
                                           "WebFinger_request", ERROR)
                            conv.trace.info(END_TAG)
                            return self.fini(session, conv)

                    if url:
                        conv.trace.request(url)
                        conv.test_output.append(
                            {"id": "-", "status": OK,
                             "message": "Found discovery URL: %s" % url})
                    else:
                        conv.test_output.append(
                            {"id": "-", "status": ERROR,
                             "message": "Failed to find discovery URL"})
                else:
                    try:
                        endp = req.endpoint
                    except AttributeError:
                        pass
                    else:
                        if not endpoint_support(conv.client, endp):
                            conv.test_output.append(
                                {"id": "-", "status": ERROR,
                                 "message": "%s not supported" % req.endpoint})
                            return self.opresult(conv, session)

                    LOGGER.info("request: %s" % req.request)
                    if req.request == "AuthorizationRequest":
                        # New state for each request
                        kwargs["request_args"].update({"state": rndstr()})
                        if not ots.client.provider_info:
                            return self.err_response(session, req.request,
                                                     "No provider info")
                    elif req.request in ["AccessTokenRequest",
                                         "UserInfoRequest",
                                         "RefreshAccessTokenRequest"]:
                        kwargs.update(
                            {"state": conv.AuthorizationRequest["state"]})
                        if not ots.client.provider_info:
                            return self.err_response(session, req.request,
                                                     "No provider info")

                    req.rm_nonstandard_args(message_factory)

                    # Extra arguments outside the OIDC spec
                    try:
                        _extra = ots.config.CLIENT["extra"][req.request]
                    except KeyError:
                        pass
                    except Exception as err:
                        return self.err_response(session, "config_extra", err)
                    else:
                        try:
                            kwargs["request_args"].update(_extra)
                        except KeyError:
                            kwargs["request_args"] = _extra

                    req.call_setup()

                    try:
                        url, body, ht_args = req.construct_request(ots.client,
                                                                   **kwargs)
                    except PyoidcError as err:  # A OIDC specific error
                        return self.err_response(session, "construct_request",
                                                 err)

                    if req.request == "AuthorizationRequest":
                        session["response_type"] = kwargs["request_args"][
                            "response_type"]
                        LOGGER.info("redirect.url: %s" % url)
                        LOGGER.info("redirect.header: %s" % ht_args)
                        conv.timestamp.append((url, utc_time_sans_frac()))
                        resp = Redirect(str(url))
                        return resp(self.environ, self.start_response)
                    else:
                        _kwargs = {"http_args": ht_args}

                        if conv.AuthorizationRequest:
                            _kwargs["state"] = conv.AuthorizationRequest[
                                "state"]

                        try:
                            _method = kwargs["method"]
                        except KeyError:
                            _method = req.method
                        try:
                            _ctype = kwargs["ctype"]
                        except KeyError:
                            _ctype = resp_c.ctype

                        self.dump_log(session, session["testid"])

                        try:
                            response = request_and_return(
                                conv, url, trace, message_factory(
                                    resp_c.response), _method, body, _ctype,
                                **_kwargs)
                        except MissingErrorResponse:
                            self.log_fault(session, "Missing Error Response",
                                           "request_response",
                                           self.get_err_type(session))
                            conv.trace.info(END_TAG)
                            return self.fini(session, conv)

                        except PyoidcError as err:
                            return self.err_response(session,
                                                     "request_and_return", err)
                        except JWKESTException as err:
                            return self.err_response(session,
                                                     "request_and_return", err)
                        except ConnectionError:
                                self.log_fault(session, "Connection Error",
                                               "request",
                                               self.get_err_type(session))
                                conv.trace.info(END_TAG)
                                return self.fini(session, conv)

                        if response is None:  # bail out
                            self.log_fault(session, "Empty response",
                                           "request_response",
                                           self.get_err_type(session))
                            conv.trace.info(END_TAG)
                            return self.fini(session, conv)

                        trace.response(response)
                        LOGGER.info(response.to_dict())

                        if expect_error:
                            session["expect_error"] = True
                            if isinstance(response, ErrorResponse):
                                if expect_error["stop"]:
                                    index = len(sequence_info["sequence"])
                                    session["index"] = index
                                    continue
                            else:
                                trace.error("Expected error, didn't get it")
                                return self.err_response(session,
                                                         "expected error", None)
                        else:
                            if resp_c.response == "RegistrationResponse":
                                if isinstance(response, RegistrationResponse):
                                    ots.client.store_registration_info(response)
                            elif resp_c.response == "AccessTokenResponse":
                                if "error" not in response:
                                    areq = conv.AuthorizationRequest.to_dict()
                                    try:
                                        del areq["acr_values"]
                                    except KeyError:
                                        pass

                try:
                    post_tests(conv, req_c, resp_c)
                except Exception as err:
                    return self.err_response(session, "post_test", err)

            index += 1
            _tid = session["testid"]
            self.dump_log(session, _tid)
            self.store_test_info(session)

        # wrap it up
        # Any after the fact tests ?
        try:
            if sequence_info["tests"]:
                conv.test_output.append(("After completing the test flow", ""))
                conv.test_sequence(sequence_info["tests"])
        except KeyError:
            pass
        except Exception as err:
            return self.err_response(session, "post_test", err)

        return self.fini(session, conv)