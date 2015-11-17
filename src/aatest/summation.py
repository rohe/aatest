import json
import os
import tarfile
from aatest import END_TAG
from aatest.check import STATUSCODE
from aatest.check import WARNING
from aatest.check import CRITICAL
from aatest.check import INCOMPLETE

__author__ = 'roland'


def trace_output(trace):
    """

    """
    element = ["Trace output\n"]
    for item in trace:
        element.append("%s" % item)
    element.append("\n")
    return element


def test_output(out):
    """

    """
    element = ["Test output\n"]
    for item in out:
        if isinstance(item, tuple):
            element.append("__%s:%s__" % item)
        else:
            element.append("[%s]" % item["id"])
            element.append("\tstatus: %s" % STATUSCODE[item["status"]])
            try:
                element.append("\tdescription: %s" % (item["name"]))
            except KeyError:
                pass
            try:
                element.append("\tinfo: %s" % (item["message"]))
            except KeyError:
                pass
    element.append("\n")
    return element


def end_tags(info):
    _ll = info["trace"].lastline()

    try:
        if _ll.endswith(END_TAG) and info["test_output"][-1] == ("X", END_TAG):
            return True
    except IndexError:
        pass

    return False


def test_summation(test_output, sid):
    status = 1
    for item in test_output:
        if isinstance(item, tuple):
            continue
        if item["status"] > status:
            status = item["status"]

    info = {
        "id": sid,
        "status": status,
        "tests": test_output
    }

    return info


def represent_result(info, session, evaluate_func=None):
    if evaluate_func is None:
        _stat = evaluate(session, info)
    else:
        _stat = evaluate_func(session, info)

    if _stat == INCOMPLETE:
        return "PARTIAL RESULT"

    if _stat < WARNING or _stat > CRITICAL:
        text = "PASSED"
    elif _stat == WARNING:
        text = "WARNING"
    else:
        text = "FAILED"

    warnings = []
    for item in info["test_output"]:
        if isinstance(item, tuple):
            continue
        elif item["status"] == WARNING:
            try:
                warnings.append(item["message"])
            except KeyError:
                pass
    if warnings:
        text = "%s\nWarnings:\n%s" % (text, "\n".join(warnings))

    return text

def pprint_json(json_txt):
    _jso = json.loads(json_txt)
    return json.dumps(_jso, sort_keys=True, indent=2, separators=(',', ': '))


def evaluate(session, info):
    _state = INCOMPLETE
    try:
        if not session["node"].complete:
            if end_tags(info):
                session["node"].complete = True
                _sum = test_summation(info["test_output"], session["testid"])
                _state = _sum["status"]
    except (AttributeError, KeyError):
        pass

    session["node"].state = _state
    return _state


def mk_tardir(issuer, test_profile):
    wd = os.getcwd()

    tardirname = wd
    for part in ["tar", issuer, test_profile]:
        tardirname = os.path.join(tardirname, part)
        if not os.path.isdir(tardirname):
            os.mkdir(tardirname)

    logdirname = os.path.join(wd, "log", issuer, test_profile)
    for item in os.listdir(logdirname):
        if item.startswith("."):
            continue

        ln = os.path.join(logdirname, item)
        tn = os.path.join(tardirname, "{}.txt".format(item))
        if not os.path.isfile(tn):
            os.symlink(ln, tn)


def create_tar_archive(issuer, test_profile):
    mk_tardir(issuer, test_profile)

    wd = os.getcwd()
    _dir = os.path.join(wd, "tar", issuer)
    os.chdir(_dir)

    tar = tarfile.open("{}.tar".format(test_profile), "w")

    for item in os.listdir(test_profile):
        if item.startswith("."):
            continue

        fn = os.path.join(test_profile, item)

        if os.path.isfile(fn):
            tar.add(fn)
    tar.close()
    os.chdir(wd)
