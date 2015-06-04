import inspect
import json
#from oic.oauth2 import SUCCESSFUL
from oic.oauth2.message import ErrorResponse
from oic.oauth2.message import MissingRequiredAttribute
from oic.oic.message import AuthorizationResponse

__author__ = 'rolandh'

import traceback
import sys

INFORMATION = 0
OK = 1
WARNING = 2
ERROR = 3
CRITICAL = 4
INTERACTION = 5

INCOMPLETE = 4

STATUSCODE = ["INFORMATION", "OK", "WARNING", "ERROR", "CRITICAL",
              "INTERACTION"]

CONT_JSON = "application/json"
CONT_JWT = "application/jwt"

END_TAG = "==== END ===="


def get_protocol_response(conv, cls):
    res = []
    for instance, msg in conv.protocol_response:
        if isinstance(instance, cls):
            res.append((instance, msg))
    return res


class Check(object):
    """ General test
    """

    cid = "check"
    msg = "OK"
    mti = True

    def __init__(self, **kwargs):
        self._status = OK
        self._message = ""
        self.content = None
        self.url = ""
        self._kwargs = kwargs

    def _func(self, conv):
        return {}

    def __call__(self, conv=None, output=None):
        _stat = self.response(**self._func(conv))
        if output is not None:
            output.append(_stat)
        return _stat

    def response(self, **kwargs):
        try:
            name = " ".join(
                [s.strip() for s in self.__doc__.strip().split("\n")])
        except AttributeError:
            name = ""

        res = {
            "id": self.cid,
            "status": self._status,
            "name": name,
            "mti": self.mti
        }

        if self._message:
            res["message"] = self._message
        else:
            if self._status != OK:
                res["message"] = self.msg

        if kwargs:
            res.update(kwargs)

        return res


class ExpectedError(Check):
    pass


class CriticalError(Check):
    status = CRITICAL


class Information(Check):
    status = INFORMATION


class Warnings(Check):
    status = WARNING


class Error(Check):
    status = ERROR


class ResponseInfo(Information):
    """Response information"""

    def _func(self, conv=None):
        self._status = self.status
        _msg = conv.last_content

        if isinstance(_msg, basestring):
            self._message = _msg
        else:
            self._message = _msg.to_dict()

        return {}


class WrapException(CriticalError):
    """
    A runtime exception
    """
    cid = "exception"
    msg = "Test tool exception"

    def _func(self, conv=None):
        self._status = self.status
        self._message = traceback.format_exception(*sys.exc_info())
        return {}


class Other(CriticalError):
    """ Other error """
    msg = "Other error"


class MissingRedirect(CriticalError):
    """ At this point in the flow a redirect back to the client was expected.
    """
    cid = "missing-redirect"
    msg = "Expected redirect to the RP, got something else"

    def _func(self, conv=None):
        self._status = self.status
        return {"url": conv.position}


class Parse(CriticalError):
    """ Parsing the response """
    cid = "response-parse"
    errmsg = "Parse error"

    def _func(self, conv=None):
        if conv.exception:
            self._status = self.status
            err = conv.exception
            self._message = "%s: %s" % (err.__class__.__name__, err)
        else:
            _rmsg = conv.response_message
            cname = _rmsg.type()
            if conv.cresp.response != cname:
                self._status = self.status
                self._message = (
                    "Didn't get a response of the type expected:",
                    " '%s' instead of '%s', content:'%s'" % (
                        cname, conv.response_type, _rmsg))
                return {
                    "response_type": conv.response_type,
                    "url": conv.position
                }

        return {}


class CheckHTTPResponse(CriticalError):
    """
    Checks that the HTTP response status is within the 200 or 300 range
    """
    cid = "check-http-response"
    msg = "OP error"

    def _func(self, conv):
        _response = conv.last_response
        _content = conv.last_content

        res = {}
        if not _response:
            return res

        if _response.status_code >= 400:
            self._status = self.status
            self._message = self.msg
            if CONT_JSON in _response.headers["content-type"]:
                try:
                    err = ErrorResponse().deserialize(_content, "json")
                    self._message = err.to_json()
                except Exception:
                    res["content"] = _content
            else:
                res["content"] = _content
            res["url"] = conv.position
            res["http_status"] = _response.status_code
        elif _response.status_code in [300, 301, 302]:
            pass
        else:
            # might still be an error message
            try:
                err = ErrorResponse().deserialize(_content, "json")
                err.verify()
                self._message = err.to_json()
                self._status = self.status
            except Exception:
                pass

            res["url"] = conv.position

        return res


class VerifyErrorResponse(ExpectedError):
    """
    Verifies that the response received by the client via redirect was an Error
    response.
    """
    cid = "verify-err-response"
    msg = "OP error"

    def _func(self, conv):
        res = {}

        response = conv.last_response
        if response.status_code == 302:
            _loc = response.headers["location"]
            if "?" in _loc:
                _query = _loc.split("?")[1]
            elif "#" in _loc:
                _query = _loc.split("#")[1]
            else:
                self._message = "Faulty error message"
                self._status = ERROR
                return

            try:
                err = ErrorResponse().deserialize(_query, "urlencoded")
                err.verify()
                #res["temp"] = err
                res["message"] = err.to_dict()
            except Exception:
                self._message = "Faulty error message"
                self._status = ERROR
        else:
            self._message = "Expected a redirect with an error message"
            self._status = ERROR

        return res


class CheckRedirectErrorResponse(ExpectedError):
    """
    Checks that the HTTP response status is outside the 200 or 300 range
    or that an error message has been received urlencoded in the form of a
    redirection.
    """
    cid = "check-redirect-error-response"
    msg = "OP error"

    def _func(self, conv):
        _response = conv.last_response

        res = {}
        try:
            _loc = _response.headers["location"]
            if "?" in _loc:
                query = _loc.split("?")[1]
            elif "#" in _loc:
                query = _loc.split("#")[1]
            else:  # ???
                self._message = "Expected a redirect"
                self._status = CRITICAL
                return res
        except (KeyError, AttributeError):
            self._message = "Expected a redirect"
            self._status = CRITICAL
            return res

        if _response.status_code == 302:
            err = ErrorResponse().deserialize(query, "urlencoded")
            try:
                err.verify()
                res["content"] = err.to_json()
                conv.protocol_response.append((err, query))
            except MissingRequiredAttribute:
                self._message = "Expected an error message"
                self._status = CRITICAL
        else:
            self._message = "Expected an error message"
            self._status = CRITICAL

        return res


class VerifyBadRequestResponse(ExpectedError):
    """
    Verifies that the OP returned a 400 Bad Request response containing a
    Error message.
    """
    cid = "verify-bad-request-response"
    msg = "OP error"

    def _func(self, conv):
        _response = conv.last_response
        _content = conv.last_content
        res = {}
        if _response.status_code == 400:
            err = ErrorResponse().deserialize(_content, "json")
            try:
                err.verify()
            except MissingRequiredAttribute:
                try:
                    self._status = self._kwargs["status"]
                except KeyError:
                    self._status = ERROR
                self._message = "Expected an error message"
            else:
                res["content"] = err.to_json()
        elif _response.status_code in [301, 302, 303]:
            pass
        elif _response.status_code < 300:
            err = ErrorResponse().deserialize(_content, "json")
            try:
                err.verify()
            except MissingRequiredAttribute:
                try:
                    self._status = self._kwargs["status"]
                except KeyError:
                    self._status = ERROR
                self._message = "Expected an error message"
            else:
                res["content"] = err.to_json()
            conv.protocol_response.append((err, _content))
        else:
            self._message = "Expected an error message"
            try:
                self._status = self._kwargs["status"]
            except KeyError:
                self._status = CRITICAL

        return res


class VerifyRandomRequestResponse(ExpectedError):
    cid = "verify-random-request-response"
    msg = "OP error"

    def _func(self, conv):
        _response = conv.last_response
        _content = conv.last_content
        res = {}
        if _response.status_code == 400:
            err = ErrorResponse().deserialize(_content, "json")
            err.verify()
            res["content"] = err.to_json()
            conv.protocol_response.append((err, _content))
            pass
        elif _response.status_code in [301, 302, 303]:
            pass
        elif _response.status_code in SUCCESSFUL:
            err = ErrorResponse().deserialize(_content, "json")
            err.verify()
            res["content"] = err.to_json()
            conv.protocol_response.append((err, _content))
        else:
            self._message = "Expected a 400 error message"
            self._status = CRITICAL

        return res


class VerifyUnknownClientIdResponse(ExpectedError):
    cid = "verify-unknown-client-id-response"
    msg = "OP error"

    def _func(self, conv):
        _response = conv.last_response
        _content = conv.last_content
        res = {}

        if _response.status_code == 400:
            err = ErrorResponse().deserialize(_content, "json")
            err.verify()
            res["content"] = err.to_json()
            conv.protocol_response.append((err, _content))
        elif _response.status_code in [301, 302, 303]:
            pass
        elif _response.status_code in SUCCESSFUL:
            err = ErrorResponse().deserialize(_content, "json")
            err.verify()
            res["content"] = err.to_json()
            conv.protocol_response.append((err, _content))
        else:
            self._message = "Expected a 400 error message"
            self._status = CRITICAL

        return res


class VerifyError(Error):
    """
    Verifies that an error message was returned and also if it's the correct
    type.
    """
    cid = "verify-error"

    def _func(self, conv):
        response = conv.last_response

        if response.status_code == 400:
            try:
                item = json.loads(response.text)
            except Exception:
                self._message = "Expected an error response"
                self._status = self.status
                return {}
        else:
            try:
                item, msg = conv.protocol_response[-1]
            except IndexError:
                self._message = "Expected a message"
                self._status = CRITICAL
                return {}

            try:
                assert item.type().endswith("ErrorResponse")
            except AssertionError:
                self._message = "Expected an error response"
                self._status = self.status
                return {}

        try:
            assert item["error"] in self._kwargs["error"]
        except AssertionError:
            self._message = "Wrong type of error, got %s" % item["error"]
            self._status = WARNING

        return {}


class CheckErrorResponse(ExpectedError):
    """
    Checks that the HTTP response status is outside the 200 or 300 range
    or that an JSON encoded error message has been received
    """
    cid = "check-error-response"
    msg = "OP error"

    def _func(self, conv):
        res = {}
        # did I get one, should only be one
        try:
            instance, _ = get_protocol_response(conv, ErrorResponse)[0]
        except ValueError:
            pass
        else:
            return res

        _response = conv.last_response
        _content = conv.last_content

        if _response.status_code >= 400:
            content_type = _response.headers["content-type"]
            if content_type is None:
                res["content"] = _content
            elif CONT_JSON in content_type:
                try:
                    self.err = ErrorResponse().deserialize(_content, "json")
                    self.err.verify()
                    res["content"] = self.err.to_json()
                except Exception:
                    res["content"] = _content
            else:
                res["content"] = _content
        elif _response.status_code in [300, 301, 302, 303]:
            pass
        else:
            # might still be an error message
            try:
                self.err = ErrorResponse().deserialize(_content, "json")
                self.err.verify()
                res["content"] = self.err.to_json()
            except Exception:
                self._message = "Expected an error message"
                self._status = CRITICAL

            res["url"] = conv.position

        return res


class VerifyErrorMessage(ExpectedError):
    """
    Checks that the last response was a JSON encoded error message
    """
    cid = "verify-error-response"
    msg = "OP error"

    def _func(self, conv):
        inst, txt = conv.protocol_response[-1]

        try:
            assert isinstance(inst, ErrorResponse)
        except AssertionError:
            self._message = "Expected an error message"
            try:
                self._status = self._kwargs["status"]
            except KeyError:
                self._status = ERROR
        else:
            try:
                assert inst["error"] in self._kwargs["error"]
            except AssertionError:
                self._message = "Unexpected error type: %s" % inst["error"]
                self._status = WARNING
            except KeyError:
                pass

        return {}


class VerifyAuthnResponse(ExpectedError):
    """
    Checks that the last response was a JSON encoded authentication message
    """
    cid = "verify-authn-response"
    msg = "OP error"

    def _func(self, conv):
        inst, txt = conv.protocol_response[-1]

        try:
            assert isinstance(inst, AuthorizationResponse)
        except AssertionError:
            self._message = "Expected an authorization response"
            self._status = ERROR

        return {}


class VerifyAuthnOrErrorResponse(ExpectedError):
    """
    Checks that the last response was a JSON encoded authentication or
    error message
    """
    cid = "authn-response-or-error"
    msg = "Expected authentication response or error message"

    def _func(self, conv):
        inst, txt = conv.protocol_response[-1]

        try:
            assert isinstance(inst, AuthorizationResponse)
        except AssertionError:
            try:
                assert isinstance(inst, ErrorResponse)
            except AssertionError:
                self._message = "Expected an authorization or error response"
                self._status = ERROR
            else:
                try:
                    assert inst["error"] in self._kwargs["error"]
                except AssertionError:
                    self._message = "Unexpected error response: %s" % inst[
                        "error"]
                    self._status = WARNING
                except KeyError:
                    pass

        return {}


class VerifyResponse(ExpectedError):
    """
    Checks that the last response was one of a possible set of OpenID Connect
    Responses
    """
    cid = "verify-response"
    msg = "Expected OpenID Connect response"

    def _func(self, conv):
        inst, txt = conv.protocol_response[-1]

        ok = False
        try:
            _status = self._kwargs["status"]
        except KeyError:
            _status = ERROR

        for cls in self._kwargs["response_cls"]:
            try:
                assert isinstance(inst, cls)
            except AssertionError:
                pass
            else:
                ok = True
                if isinstance(inst, ErrorResponse):
                    try:
                        assert inst["error"] in self._kwargs["error"]
                    except AssertionError:
                        self._message = "Unexpected error response: %s" % inst[
                            "error"]
                        self._status = WARNING
                        return {}
                    except KeyError:
                        pass

                break

        if not ok:
            self._message = "Got a %s response" % inst.__class__.__name__
            self._status = _status

        return {}


def factory(cid, classes):
    if len(classes) == 0:
        for name, obj in inspect.getmembers(sys.modules[__name__]):
            if inspect.isclass(obj):
                try:
                    classes[obj.cid] = obj
                except AttributeError:
                    pass

    if cid in classes:
        return classes[cid]
    else:
        return None
