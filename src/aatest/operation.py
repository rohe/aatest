import copy
import json
import logging
import functools
from oic.utils.http_util import Response
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
    return instance.conv.client.http_request(url, method)


class Operation(object):
    _tests = {"pre": [], "post": []}

    def __init__(self, conv, profile, test_id, conf, funcs, check_factory):
        self.conv = conv
        self.funcs = funcs
        self.test_id = test_id
        self.conf = conf
        self.profile = profile.split('.')
        self.req_args = {}
        self.op_args = {}
        self.expect_exception = None
        self.sequence = []
        self.skip = False
        self.check_factory = check_factory
        # detach
        self.tests = copy.deepcopy(self._tests)

        # Monkey-patch: make sure we use the same http session (preserving
        # cookies) when fetching keys from issuers 'jwks_uri' as for the
        # rest of the test sequence
        import oic.utils.keyio

        oic.utils.keyio.request = functools.partial(
            request_with_client_http_session, self)

    def run(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        if self.skip:
            return
        else:
            if self.tests["pre"] or self.tests["post"]:
                _ver = Verify(self.check_factory, self.conv.msg_factory,
                              self.conv)
            else:
                _ver = None

            if self._tests["pre"]:
                _ver.test_sequence(self.tests["pre"])
            res = self.run(*args, **kwargs)
            if res:
                return res
            if self.tests["post"]:
                _ver.test_sequence(self.tests["post"])

    def _setup(self):
        if self.skip:  # Don't bother
            return

        for op, arg in self.funcs.items():
            op(self, arg)

    def map_profile(self, profile_map):
        try:
            funcs = profile_map[self.__class__][self.profile[0]]
        except KeyError:
            self.skip = True
        else:
            if funcs is None:
                self.skip = True
            else:
                for op, arg in funcs.items():
                    op(self, arg)

    def op_setup(self):
        pass

    def setup(self, profile_map):
        """
        Order between setup methods are significant

        :param profile_map:
        :return:
        """
        self.map_profile(profile_map)
        self.op_setup()
        self._setup()

    def catch_exception(self, func, **kwargs):
        res = None
        try:
            self.conv.trace.info(
                "Running {} with kwargs: {}".format(func, kwargs))
            res = func(**kwargs)
        except Exception as err:
            if not self.expect_exception:
                raise
            elif not isinstance(err, self.expect_exception):
                raise
            else:
                self.conv.trace.info("Got expected exception {}".format(err))
        else:
            if self.expect_exception:
                raise Exception(
                    "Expected exception '{}'.".format(self.expect_exception))
            self.conv.trace.reply(res)

        return res


class Notice(object):
    def __init__(self):
        self.template = ""

    def __call__(self, lookup, environ, start_response, **kwargs):
        resp = Response(mako_template=self.template,
                        template_lookup=lookup,
                        headers=[])
        return resp(environ, start_response, **kwargs)


class Note(Notice):
    def __init__(self):
        Notice.__init__(self)
        self.template = "note.mako"
