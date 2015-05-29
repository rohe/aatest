import json
import logging

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


class Operation(object):
    def __init__(self, conv, profile, test_id, conf, funcs):
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

    def run(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        if self.skip:
            return
        else:
            self.run(*args, **kwargs)

    def _setup(self):
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

    def setup(self, profile_map):
        self.map_profile(profile_map)
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
