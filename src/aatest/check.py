import inspect
import traceback
import sys
from aatest.events import EV_CONDITION
from aatest.events import EV_RESPONSE
from aatest.events import EV_HTTP_RESPONSE

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

STATUSCODE_TRANSL = dict([(STATUSCODE[i], i) for i in range(len(STATUSCODE))])

CONT_JSON = "application/json"
CONT_JWT = "application/jwt"


class State(object):
    name = 'state'

    def __init__(self, test_id, status, name='', mti=False, message='',
                 context='', **kwargs):
        self.test_id = test_id
        self.status = status
        self.name = name
        self.mti = mti
        self.message = message
        self.context = context
        self.kwargs = kwargs

    def __str__(self):
        _info = {
            'ctx': self.context, 'id': self.test_id,
            'stat': STATUSCODE[self.status], 'msg': self.message
        }
        if self.status != OK:
            if self.context:
                txt = '{ctx}:{id}: status={stat}, message={msg}'.format(
                    **_info)
            else:
                txt = '{id}: status={stat}, message={msg}'.format(**_info)
        else:
            if self.context:
                txt = '{ctx}:{id}: status={stat}'.format(**_info)
            else:
                txt = '{id}: status={stat}'.format(**_info)

        if self.name:
            txt = '{} [{}]'.format(txt, self.name)

        return txt


def assert_summation(events, sid):
    status = OK
    result = []
    for test_result in events.get_data(EV_CONDITION):
        result.append('{}'.format(test_result))
        if test_result.status > status:
            status = test_result.status

    info = {
        "id": sid,
        "status": status,
        "assertions": result
    }

    return info


class Check(object):
    """ General test
    """

    cid = "check"
    msg = "OK"
    mti = True
    state_cls = State

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

        res = self.state_cls(test_id=self.cid, status=self._status, name=name,
                             mti=self.mti)

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
        _msg = conv.events.last_item(EV_RESPONSE)

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


class CheckHTTPResponse(CriticalError):
    """
    Checks that the HTTP response status is within a specified range
    """
    cid = "http_response"
    msg = "Incorrect HTTP status_code"

    def _func(self, conv):
        _response = conv.events.last_item(EV_HTTP_RESPONSE)

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
