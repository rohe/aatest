import copy
import inspect
import json
import logging
import time
import sys

from oic.utils.http_util import Response
from aatest.events import EV_PROTOCOL_RESPONSE

from aatest.verify import Verify

logger = logging.getLogger(__name__)


def print_result(resp):
    try:
        cl_name = resp.__class__.__name__
    except AttributeError:
        cl_name = ""
        txt = resp
    else:
        txt = json.dumps(resp.to_dict(), sort_keys=True, indent=2,
                         separators=(',', ': '))

    logger.info("{}: {}".format(cl_name, txt))


def request_with_client_http_session(instance, method, url, **kwargs):
    """Use the clients http session to make http request.
    Note: client.http_request function requires the parameters in reverse
    order (compared to the requests library): (method, url) vs (url, method)
    so we can't bind the instance method directly.
    """
    return instance.conv.entity.http_request(url, method)


class Operation(object):
    _tests = {"pre": [], "post": []}

    def __init__(self, conv, inut, sh, test_id='', conf=None, funcs=None,
                 check_factory=None, cache=None, profile='', **kwargs):
        self.conv = conv
        self.inut = inut
        self.sh = sh
        self.funcs = funcs or {}
        self.test_id = test_id
        self.conf = conf
        self.check_factory = check_factory
        self.cache = cache
        self.profile = profile
        self.req_args = {}
        self.op_args = {}
        self.expect_exception = None
        self.expect_error = None
        self.sequence = []
        self.skip = False
        self.allowed_status_codes = [200]
        # detach
        self.tests = copy.deepcopy(self._tests)

    def run(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        if self.skip:
            return
        else:
            cls_name = self.__class__.__name__
            if self.tests["pre"] or self.tests["post"]:
                _ver = Verify(self.check_factory, self.conv, cls_name=cls_name)
            else:
                _ver = None

            if self.tests["pre"]:
                _ver.test_sequence(self.tests["pre"])

            self.conv.trace.info("Running '{}'".format(cls_name))
            res = self.run(*args, **kwargs)

            if self.tests["post"]:
                _ver.test_sequence(self.tests["post"])

            if res:
                return res

    def _setup(self):
        if self.skip:  # Don't bother
            return

        for op, arg in list(self.funcs.items()):
            op(self, arg)

    def map_profile(self, profile_map):
        pass

    def op_setup(self):
        pass

    def setup(self, profile_map=None):
        """
        Order between setup methods are significant

        :param profile_map:
        :return:
        """
        if profile_map:
            self.map_profile(profile_map)
        self.op_setup()
        self._setup()

    def catch_exception(self, func, **kwargs):
        res = None
        try:
            self.conv.trace.info(
                "Running {} with kwargs: {}".format(func.__name__, kwargs))
            res = func(**kwargs)
        except Exception as err:
            if not self.expect_exception:
                raise
            elif not err.__class__.__name__ == self.expect_exception:
                raise
            else:
                self.conv.trace.info("Got expected exception: {}".format(err))
        else:
            if self.expect_exception:
                raise Exception(
                    "Expected exception '{}'.".format(self.expect_exception))
            if res:
                self.conv.trace.reply(res)
                self.conv.events.store(EV_PROTOCOL_RESPONSE, res,
                                       sender='catch_exception')

        return res

    def handle_response(self, *args):
        raise NotImplemented

    def handle_request(self, *args):
        raise NotImplemented


class Notice(Operation):
    template = ""

    def __init__(self, conv, inut, sh, **kwargs):
        Operation.__init__(self, conv, inut, sh, **kwargs)
        self.message = ""

    def args(self):
        return {}

    def __call__(self, *args, **kwargs):
        resp = Response(mako_template=self.template,
                        template_lookup=self.inut.lookup,
                        headers=[])
        return resp(self.inut.environ, self.inut.start_response,
                    **self.args())


class Note(Notice):
    template = "note.mako"

    def op_setup(self):
        self.message = self.conv.flow["note"]

    def args(self):
        return {
            "url": "%scontinue?path=%s&index=%d" % (
                self.inut.conf.BASE, self.test_id, self.sh.session["index"]),
            "back": self.inut.conf.BASE,
            "note": self.message,
        }


class TimeDelay(Operation):
    def __init__(self, conv, inut, sh, **kwargs):
        Operation.__init__(self, conv, inut, sh, **kwargs)
        self.delay = 30

    def __call__(self, *args, **kwargs):
        time.sleep(self.delay)
        return None


def factory(name):
    for fname, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj):
            if name == fname:
                return obj
