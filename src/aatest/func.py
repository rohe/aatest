import inspect
import sys

__author__ = 'roland'


def set_request_args(oper, args):
    oper.req_args.update(args)


def set_op_args(oper, args):
    oper.op_args.update(args)


def cache_events(oper, arg):
    key = oper.conv.test_id
    oper.conv.cache[key] = oper.conv.events.events[:]


def restore_events(oper, arg):
    _events = oper.conv.events
    _cache = oper.conv.cache
    key = oper.conv.test_id

    if len(_events):
        for x in _cache[key][:]:
            if x not in _events:
                _events.append(x)
        _events.sort()
    else:
        oper.conv.events = _cache[key]

    del _cache[key]


def skip_operation(oper, arg):
    if oper.profile[0] in arg["flow_type"]:
        oper.skip = True


def expect_exception(oper, args):
    oper.expect_exception = args


def conditional_expect_exception(oper, args):
    condition = args["condition"]
    exception = args["exception"]

    res = True
    for key in list(condition.keys()):
        try:
            assert oper.req_args[key] in condition[key]
        except KeyError:
            pass
        except AssertionError:
            res = False

    try:
        if res == args["oper"]:
            oper.expect_exception = exception
    except KeyError:
        if res is True:
            oper.expect_exception = exception


def add_post_condition(oper, args):
    for key, item in args.items():
        oper.tests['post'].append((key, item))


def add_pre_condition(oper, args):
    for key, item in args.items():
        oper.tests['pre'].append((key, item))


def set_allowed_status_codes(oper, args):
    oper.allowed_status_codes = args


def set_time_delay(oper, args):
    oper.delay = args


def clear_cookies(oper, args):
    oper.client.cookiejar.clear()


def factory(name):
    for fname, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isfunction(obj):
            if fname == name:
                return obj

    return None