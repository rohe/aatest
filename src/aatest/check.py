import inspect
import traceback
import sys

__author__ = 'rolandh'


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
    for instance, msg in conv.events.get('protocol_response'):
        if isinstance(instance, cls):
            res.append((instance, msg))
    return res


class TestResult(object):
    name = 'test_result'

    def __init__(self, test_id, status, name, mti=False):
        self.test_id = test_id
        self.status = status
        self.name = name
        self.mti = mti
        self.message = ''
        self.http_status = 0
        self.cid = ''

    def __str__(self):
        if self.status:
            return '{}: status={}, message={}'.format(self.test_id,
                                                      STATUSCODE[self.status],
                                                      self.message)
        else:
            return '{}: status={}'.format(self.test_id, STATUSCODE[self.status])


class Check(object):
    """ General test
    """

    cid = "check"
    msg = "OK"
    mti = True
    test_result_cls = TestResult

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
                [str(s).strip() for s in self.__doc__.strip().split("\n")])
        except AttributeError:
            name = ""

        res = self.test_result_cls(test_id=self.cid, status=self._status,
                                   name=name, mti=self.mti)

        if self._message:
            res.message = self._message
        else:
            if self._status != OK:
                res.message = self.msg

        for key, val in kwargs.items():
            setattr(self, key, val)

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

        if isinstance(_msg, str):
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
    Checks that the HTTP response status is within a specified range
    """
    cid = "http_response"
    msg = "Incorrect HTTP status_code"

    def _func(self, conv):
        _response = conv.events.last_item('response')

        res = {}
        if not _response:
            return res

        if 'status_code' in self._kwargs:
            if _response.status_code not in self._kwargs['status_code']:
                self._status = self.status
                self._message = self.msg
                res["http_status"] = _response.status_code
        else:
            if _response.status_code >= 400:
                self._status = self.status
                self._message = self.msg
                res["http_status"] = _response.status_code

        return res


def factory(cid):
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj):
            try:
                if obj.cid == cid:
                    return obj
            except AttributeError:
                pass

    return None
