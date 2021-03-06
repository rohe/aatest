from __future__ import print_function
import json
import logging
import time
import traceback
import requests
import sys
from subprocess import Popen, PIPE
from oic.oauth2 import HttpError

__author__ = 'rolandh'
__version__ = "0.1.0"

LOCAL_PATH = "export/"
END_TAG = "==== END ===="

CRYPTSUPPORT = {"none": "n", "signing": "s", "encryption": "e"}


class AATestError(Exception):
    pass


class FatalError(AATestError):
    pass


class Break(AATestError):
    pass


class Unknown(AATestError):
    pass


class ConfigurationError(AATestError):
    pass


class NotSupported(AATestError):
    pass


class RequirementsNotMet(AATestError):
    pass


class CheckError(AATestError):
    pass


class OperationError(AATestError):
    pass


class ConditionError(FatalError):
    pass


def as_bytes(s):
    """
    Convert an unicode string to bytes.
    :param s: Unicode / bytes string
    :return: bytes string
    """
    try:
        s = s.encode("utf-8", 'replace')
    except (AttributeError, UnicodeDecodeError):
        pass
    return s


def as_unicode(b):
    """
    Convert a byte string to a unicode string
    :param b: byte string
    :return: unicode string
    """
    try:
        b = b.decode()
    except (AttributeError, UnicodeDecodeError):
        pass
    return b


class Trace(object):
    def __init__(self, absolut_start=False):
        self.trace = []
        self.start = time.time()
        if absolut_start:
            self.trace.append("Trace init: {}".format(
                time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())))

    @staticmethod
    def format(resp):
        raise NotImplemented()

    def request(self, msg):
        delta = time.time() - self.start
        self.trace.append("%f --> %s" % (delta, msg))

    def reply(self, msg):
        delta = time.time() - self.start
        self.trace.append("%f <-- %s" % (delta, msg))

    def response(self, resp):
        raise NotImplemented()

    def info(self, msg):
        delta = time.time() - self.start
        self.trace.append("%f %s" % (delta, msg))

    def error(self, msg):
        delta = time.time() - self.start
        self.trace.append("%f [ERROR] %s" % (delta, msg))

    def warning(self, msg):
        delta = time.time() - self.start
        self.trace.append("%f [WARNING] %s" % (delta, msg))

    def __str__(self):
        return "\n".join([as_unicode(t) for t in self.trace])

    def clear(self):
        self.trace = []

    def __getitem__(self, item):
        return self.trace[item]

    def __next__(self):
        for line in self.trace:
            yield line

    def lastline(self):
        try:
            return self.trace[-1]
        except IndexError:
            return ""


def start_script(path, wdir="", *args):
    if not path.startswith("/"):
        popen_args = ["./" + path]
    else:
        popen_args = [path]

    popen_args.extend(args)
    if wdir:
        return Popen(popen_args, stdout=PIPE, stderr=PIPE, cwd=wdir)
    else:
        return Popen(popen_args, stdout=PIPE, stderr=PIPE)


def stop_script_by_name(name):
    import subprocess
    import signal
    import os

    p = subprocess.Popen(['ps', '-A'], stdout=subprocess.PIPE)
    out, err = p.communicate()

    for line in out.splitlines():
        if name in line:
            pid = int(line.split(None, 1)[0])
            os.kill(pid, signal.SIGKILL)


def stop_script_by_pid(pid):
    import signal
    import os

    os.kill(pid, signal.SIGKILL)


def get_page(url):
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.text
    else:
        raise HttpError(resp.status_code)


def exception_trace(tag, exc, log=None):
    message = traceback.format_exception(*sys.exc_info())
    if log:
        if isinstance(exc, Exception):
            log.error("[%s] ExcList: %s" % (tag, "".join(message),))
        log.error("[%s] Exception: %s" % (tag, exc))
    else:
        if isinstance(exc, Exception):
            print("[%s] ExcList: %s" % (tag, "".join(message),),
                  file=sys.stderr)
        try:
            print("[%s] Exception: %s" % (tag, exc), file=sys.stderr)
        except UnicodeEncodeError:
            print("[%s] Exception: %s" % (
                tag, exc.message.encode("utf-8", "replace")), file=sys.stderr)


class Node(object):
    def __init__(self, name, desc="", rmc=False, experr=False,
            tests=None, **kwargs):
        self.name = name
        self.desc = desc
        self.state = 0
        self.rmc = rmc
        self.experr = experr
        self.tests = tests or {}
        self.kwargs = kwargs


def make_node(x, spec):
    return Node(x, **spec)


def get_node(tests, nid):
    l = [x for x in tests if x.name == nid]
    try:
        return l[0]
    except (ValueError, IndexError):
        return None


class ContextFilter(logging.Filter):
    """
    This is a filter which injects time laps information into the log.
    """

    def start(self):
        self.start = time.time()

    def filter(self, record):
        record.delta = time.time() - self.start
        return True


def jlog(logger, typ, item):
    func = getattr(logger, typ)
    func(json.dumps(item, indent=2, sort_keys=True))


def resp2json(resp):
    return {'message': resp.message, 'status': resp.status,
            'headers': resp.headers}
