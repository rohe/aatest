import json
import traceback
import logging
from aatest.interaction import Interaction

from oic.oauth2 import SUCCESSFUL
from oic.oauth2 import verify_header
from oic.oauth2 import ParseError
from oic.oauth2 import ErrorResponse
from oic.oauth2 import HttpError
from oic.oauth2 import OtherError
import sys

from aatest import FatalError
from aatest import Trace
from aatest.check import State
from aatest.events import Events

__author__ = 'roland'

logger = logging.getLogger(__name__)


class Conversation(object):
    def __init__(self, flow, entity, msg_factory, check_factory=None,
                 features=None, trace_cls=Trace, interaction=None,
                 **extra_args):
        self.flow = flow
        self.entity = entity
        self.msg_factory = msg_factory
        self.trace = trace_cls(True)
        self.test_id = ""
        self.info = {}
        self.index = 0
        self.comhandler = None
        self.check_factory = check_factory
        self.features = features
        self.extra_args = extra_args
        self.exception = None
        self.events = Events()
        self.sequence = []

        try:
            self.callback_uris = extra_args["callback_uris"]
        except KeyError:
            pass

        self.trace.info('Conversation initiated')
        self.interaction = Interaction(self.entity, interaction)

    def for_me(self, url):
        for cb in self.callback_uris:
            if url.startswith(cb):
                return True
        return False

    def err_check(self, test, err=None, bryt=True):
        if err:
            self.exception = err
        chk = self.check_factory(test)()
        chk(self, self.events.last('condition'))
        if bryt:
            e = FatalError("%s" % err)
            e.trace = "".join(traceback.format_exception(*sys.exc_info()))
            raise e

    def my_endpoints(self):
        return self.entity.redirect_uris

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
            "sequence": self.flow,
            "flow_index": self.index,
            "client_config": self.entity.conf,
            "condition": self.events.get('condition')
        }

        try:
            state["client"][
                "registration_resp"] = \
                self.entity.registration_response.to_json()
        except AttributeError:
            pass

        txt = json.dumps(state)
        _fh = open(filename, "w")
        _fh.write(txt)
        _fh.close()

    def do_interaction(self, url, content, response):
        _base = url.split("?")[0]

        try:
            _spec = self.interaction.pick_interaction(_base, content)
        except InteractionNeeded:
            if self.extra_args["break"]:
                self.dump_state(self.extra_args["break"])
                exit(2)

            self.events.store('position', url)
            self.trace.error("Page Content: %s" % content)
            raise
        except KeyError:
            self.events.store('position', url)
            self.trace.error("Page Content: %s" % content)
            self.err_check("interaction-needed")
            raise

        if _spec is None:
            return response

        if len(_spec) > 2:
            self.trace.info(">> %s <<" % _spec["page-type"])
            if _spec["page-type"] == "login":
                self.events.store('login_page', content)

        _op = Action(_spec["control"])

        try:
            _response = _op(self.entity, self, self.trace, url,
                            response, content, self.features)
            if isinstance(_response, dict):
                self.events.store('response', _response)
                # self.events.store('last_content', _response)
                return _response

            content = _response.text
            self.events.store('position', url)
            self.events.store('content', content)
            self.events.store('response', _response)
            return _response

        except (FatalError, InteractionNeeded):
            raise
        except Exception as err:
            self.err_check("exception", err, False)
            self.events.store('condition',
                              State(status=3, test_id="Communication error",
                                    message="{}".format(err)))
            raise FatalError

    def intermit(self, response):
        if response.status_code >= 400:
            done = True
        else:
            done = False

        content = response.text
        rdseq = []
        while not done:
            url = response.url

            while response.status_code in [302, 301, 303]:
                url = response.headers["location"]
                if url in rdseq:
                    raise FatalError("Loop detected in redirects")
                else:
                    rdseq.append(url)
                    if len(rdseq) > 8:
                        raise FatalError(
                            "Too long sequence of redirects: %s" % rdseq)

                self.trace.reply("REDIRECT TO: %s" % url)

                # If back to me
                if self.for_me(url):
                    done = True
                    break
                else:
                    try:
                        response = self.entity.send(
                            url, "GET",
                            headers={"Referer": self.events.last('position')})
                    except Exception as err:
                        raise FatalError("%s" % err)

                    content = response.text
                    self.trace.reply("CONTENT: %s" % content)
                    self.events.store('response', response)

                    if response.status_code >= 400:
                        done = True
                        break

            if done or url is None:
                break

            response = self.do_interaction(url, content, response)

            if response.status_code < 300 or response.status_code >= 400:
                break

        return response

    def parse_request_response(self, reqresp, response, body_type, state="",
                               **kwargs):

        text = reqresp.text
        if reqresp.status_code in SUCCESSFUL:
            body_type = verify_header(reqresp, body_type)
        elif reqresp.status_code == 302:  # redirect
            text = reqresp.headers["location"]
        elif reqresp.status_code == 500:
            logger.error("(%d) %s" % (reqresp.status_code, reqresp.text))
            raise ParseError("ERROR: Something went wrong: %s" % reqresp.text)
        elif reqresp.status_code in [400, 401]:
            # expecting an error response
            if issubclass(response, ErrorResponse):
                pass
        else:
            logger.error("(%d) %s" % (reqresp.status_code, reqresp.text))
            raise HttpError("HTTP ERROR: %s [%s] on %s" % (
                reqresp.text, reqresp.status_code, reqresp.url))

        if body_type:
            if response:
                return self.entity.parse_response(response, text,
                                                  body_type, state, **kwargs)
            else:
                raise OtherError("Didn't expect a response body")
        else:
            return reqresp
