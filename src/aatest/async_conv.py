import http.cookiejar
import json
import sys
import traceback
from oic.exception import PyoidcError
from oic.oauth2 import rndstr
from oic.oic import ProviderConfigurationResponse
from oic.oic import RegistrationResponse

from aatest.opfunc import Operation
from aatest import FatalError
from aatest import Break
from aatest.check import ExpectedError, TestResult
from aatest.check import INTERACTION
from aatest.events import Events
from aatest.interaction import Interaction
from aatest.interaction import Action
from aatest.interaction import InteractionNeeded
from aatest.status import STATUSCODE


__author__ = 'rolandh'


class Conversation(object):
    """
    :param response: The received HTTP messages
    :param protocol_response: List of the received protocol messages
    """

    def __init__(self, client, config, trace, interaction,
                 check_factory=None, msg_factory=None,
                 features=None, verbose=False, expect_exception=None,
                 **extra_args):
        self.entity = client
        self.entity_config = config
        self.trace = trace
        self.features = features
        self.verbose = verbose
        self.check_factory = check_factory
        self.msg_factory = msg_factory
        self.expect_exception = expect_exception
        self.extra_args = extra_args

        self.cjar = {"browser": http.cookiejar.MozillaCookieJar(),
                     "rp": http.cookiejar.MozillaCookieJar(),
                     "service": http.cookiejar.MozillaCookieJar()}

        self.events = Events()
        self.interaction = Interaction(self.entity, interaction)
        self.exception = None
        self.provider_info = self.entity.provider_info or {}
        self.interact_done = []
        self.ignore_check = []
        self.login_page = ""
        self.sequence = {}
        self.flow_index = 0
        self.request_args = {}
        self.args = {}
        self.creq = None
        self.cresp = None
        self.req = None
        self.request_spec = None
        self.last_url = ""
        self.state = rndstr()

    def check_severity(self, stat):
        if stat["status"] >= 4:
            self.trace.error("WHERE: %s" % stat["id"])
            self.trace.error("STATUS:%s" % STATUSCODE[stat["status"]])
            try:
                self.trace.error("HTTP STATUS: %s" % stat["http_status"])
            except KeyError:
                pass
            try:
                self.trace.error("INFO: %s" % (stat["message"],))
            except KeyError:
                pass

            if not stat["mti"]:
                raise Break(stat["message"])
            else:
                raise FatalError(stat["message"])

    def do_check(self, test, **kwargs):
        if isinstance(test, str):
            chk = self.check_factory(test)(**kwargs)
        else:
            chk = test(**kwargs)

        if chk.__class__.__name__ not in self.ignore_check:
            stat = chk(self, self.events.last('condition').data)
            self.check_severity(stat)

    def err_check(self, test, err=None, bryt=True):
        if err:
            self.exception = err
        chk = self.check_factory(test)()
        chk(self, self.events.last('condition').data)
        if bryt:
            e = FatalError("%s" % err)
            e.trace = "".join(traceback.format_exception(*sys.exc_info()))
            raise e

    def test_sequence(self, sequence):
        if isinstance(sequence, dict):
            for test, kwargs in list(sequence.items()):
                self.do_check(test, **kwargs)
        else:
            for test in sequence:
                if isinstance(test, tuple):
                    test, kwargs = test
                else:
                    kwargs = {}
                self.do_check(test, **kwargs)
                if test == ExpectedError:
                    return False
        return True

    def my_endpoints(self):
        return []

    def for_me(self, response="", url=""):
        if not response:
            response = self.events.last('response').data
        if not url:
            url = response.headers["location"]
        for redirect_uri in self.my_endpoints():
            if url.startswith(redirect_uri):
                return True
        return False

    def intermit(self):
        _response = self.events.last('response').data
        if _response.status_code >= 400:
            done = True
        else:
            done = False

        rdseq = []
        while not done:
            url = _response.url
            content = _response.text

            while _response.status_code in [302, 301, 303]:
                url = _response.headers["location"]
                if url in rdseq:
                    raise FatalError("Loop detected in redirects")
                else:
                    rdseq.append(url)
                    if len(rdseq) > 8:
                        raise FatalError(
                            "Too long sequence of redirects: %s" % rdseq)

                self.trace.reply("REDIRECT TO: %s" % url)

                # If back to me
                if self.for_me(_response):
                    self.entity.cookiejar = self.cjar["rp"]
                    done = True
                    break
                else:
                    try:
                        _response = self.entity.send(
                            url, "GET", headers={"Referer": self.last_url})
                    except Exception as err:
                        raise FatalError("%s" % err)

                    content = _response.text
                    self.trace.reply("CONTENT: %s" % content)
                    self.events.store('position', url)
                    self.events.store('content', content)
                    self.response = _response

                    if _response.status_code >= 400:
                        done = True
                        break

            if done or url is None:
                break

            _base = url.split("?")[0]

            try:
                _spec = self.interaction.pick_interaction(_base, content)
                #if _spec in self.interact_done:
                #    self.trace.error("Same interaction a second time")
                #    raise InteractionNeeded("Same interaction twice")
                #self.interact_done.append(_spec)
            except InteractionNeeded:
                if self.extra_args["break"]:
                    self.dump_state(self.extra_args["break"])
                    exit(2)

                self.position = url
                self.trace.error("Page Content: %s" % content)
                raise
            except KeyError:
                self.position = url
                self.trace.error("Page Content: %s" % content)
                self.err_check("interaction-needed")

            if len(_spec) > 2:
                self.trace.info(">> %s <<" % _spec["page-type"])
                if _spec["page-type"] == "login":
                    self.login_page = content

            _op = Action(_spec["control"])

            try:
                _response = _op(self.entity, self, self.trace, url,
                                _response, content, self.features)
                if isinstance(_response, dict):
                    self.events.store('response', _response)
                    return _response
                self.events.store('position', url)
                self.events.store('http response', _response)
                self.events.store('received', _response.text)

                if _response.status_code >= 400:
                    break

            except (FatalError, InteractionNeeded):
                raise
            except Exception as err:
                self.err_check("exception", err, False)
                self.events.store('condition',
                                  TestResult(test_id="Communication error", status=3, message="{}".format(err)))
                raise FatalError

        self.events.store('http response', _response)
        try:
            self.events.store('content', _response.text)
        except AttributeError:
            self.events.store('content', None)

    def init(self, phase):
        self.creq, self.cresp = phase

    def setup_request(self):
        self.request_spec = req = self.creq(conv=self)

        if isinstance(req, Operation):
            for intact in self.interaction.interactions:
                try:
                    if req.__class__.__name__ == intact["matches"]["class"]:
                        req.args = intact["args"]
                        break
                except KeyError:
                    pass
        else:
            try:
                self.request_args = req.request_args
            except KeyError:
                pass
            try:
                self.args = req.kw_args
            except KeyError:
                pass

        # The authorization dance is all done through the browser
        if req.request == "AuthorizationRequest":
            self.entity.cookiejar = self.cjar["browser"]
        # everything else by someone else, assuming the RP
        else:
            self.entity.cookiejar = self.cjar["rp"]

        self.req = req

    def send(self):
        pass

    def handle_result(self):
        pass

    def do_query(self):
        self.setup_request()
        self.send()
        last_response = self.events.last('response').data
        if last_response.status_code in [301, 302, 303] and \
                not self.for_me():
            self.intermit()
        if not self.handle_result():
            self.intermit()
            self.handle_result()

    def do_sequence(self, oper):
        self.sequence = oper
        try:
            self.test_sequence(oper["tests"]["pre"])
        except KeyError:
            pass

        for i in range(self.flow_index, len(oper["sequence"])):
            phase = oper["sequence"][i]
            flow = oper["flow"][i]
            self.flow_index = i

            self.trace.info(flow)
            if not isinstance(phase, tuple):
                _proc = phase()
                _proc(self)
                continue

            self.init(phase)

            try:
                _cimp = self.extra_args["cookie_imp"]
            except KeyError:
                pass
            else:
                if self.creq.request == "AuthorizationRequest" and _cimp:
                    try:
                        self.cjar['browser'].load(_cimp)
                    except Exception:
                        self.trace.error("Could not import cookies from file")

            try:
                _kaka = self.extra_args["login_cookies"]
            except KeyError:
                pass
            else:
                self.entity.cookiejar = self.cjar["browser"]
                self.entity.load_cookies_from_file(_kaka.name)

            try:
                self.do_query()
            except InteractionNeeded:
                self.events.store('condition',
                                  TestResult(status=INTERACTION,
                                   message=self.events.last_item('received'),
                                   test_id="exception",
                                   name="interaction needed",
                                   url=self.position))
                break
            except FatalError:
                raise
            except PyoidcError as err:
                if err.message:
                    self.trace.info("Protocol message: %s" % err.message)
                raise FatalError
            except Exception as err:
                #self.err_check("exception", err)
                raise
            else:
                if self.extra_args["cookie_exp"]:
                    if self.request_spec.request == "AuthorizationRequest":
                        self.cjar["browser"].save(
                            self.extra_args["cookie_exp"], ignore_discard=True)

        try:
            self.test_sequence(oper["tests"]["post"])
        except KeyError:
            pass

    def dump_state(self, filename):
        state = {
            "client": {
                "behaviour": self.entity.behaviour,
                "keyjar": self.entity.keyjar.dump(),
                "provider_info": self.entity.provider_info.to_json(),
                "client_id": self.entity.client_id,
                "client_secret": self.entity.client_secret,
            },
            "trace_log": {"start": self.trace.start, "trace": self.trace.trace},
            "sequence": self.sequence["flow"],
            "flow_index": self.flow_index,
            "entity_config": self.entity_config,
            "condition checks": self.events.get('condition')
        }

        try:
            state["client"][
                "registration_resp"] = self.entity.registration_response.to_json()
        except AttributeError:
            pass

        txt = json.dumps(state)
        _fh = open(filename, "w")
        _fh.write(txt)
        _fh.close()

    # def restore_state(self, filename):
    #     txt = open(filename).read()
    #     state = json.loads(txt)
    #     self.trace.start = state["trace_log"]["start"]
    #     self.trace.trace = state["trace_log"]["trace"]
    #     self.flow_index = state["flow_index"]
    #     self.entity_config = state["entity_config"]
    #     self.condition_checks = state["condition checks"]
    #
    #     self.entity.behaviour = state["client"]["behaviour"]
    #     self.entity.keyjar.restore(state["client"]["keyjar"])
    #     pcr = ProviderConfigurationResponse().from_json(
    #         state["client"]["provider_info"])
    #     self.entity.provider_info = pcr
    #     self.entity.client_id = state["client"]["client_id"]
    #     self.entity.client_secret = state["client"]["client_secret"]
    #
    #     for key, val in list(pcr.items()):
    #         if key.endswith("_endpoint"):
    #             setattr(self.entity, key, val)
    #
    #     try:
    #         self.entity.registration_response = RegistrationResponse().from_json(
    #             state["client"]["registration_resp"])
    #     except KeyError:
    #         pass

    def restart(self, state):
        pass