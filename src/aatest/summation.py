import json
import os
import tarfile
from aatest import END_TAG
from aatest.check import WARNING
from aatest.check import CRITICAL
from aatest.check import INCOMPLETE
from aatest.check import assert_summation

__author__ = 'roland'


def trace_output(trace):
    """

    """
    element = ["Trace output\n"]
    for item in trace:
        element.append("%s" % item)
    element.append("\n")
    return element


def condition(events, html=False):
    """

    """
    if html:
        element = ["<h3>Conditions</h3>", "<pre><code>"]
    else:
        element = ["Conditions\n"]
    for cond in events.get_data('condition'):
        element.append('{}'.format(cond))
    if html:
        element.append("</code></pre>")
        return "\n".join(element)
    else:
        element.append("\n")
        return element


def end_tags(info):
    _ll = info["trace"].lastline()

    try:
        if _ll.endswith(END_TAG) and info["condition"][-1] == END_TAG:
            return True
    except IndexError:
        pass

    return False


def represent_result(info, state):
    if state == INCOMPLETE:
        return "PARTIAL RESULT"

    if state < WARNING or state > CRITICAL:
        text = "PASSED"
    elif state == WARNING:
        text = "WARNING"
    else:
        text = "FAILED"

    warnings = []
    for state in info["events"].get_data('condition'):
        if state.status == WARNING:
            text = 'WARNING'
            try:
                warnings.append(state.message)
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
                _sum = assert_summation(info["condition"], session["testid"])
                _state = _sum["status"]
    except (AttributeError, KeyError):
        pass

    session["node"].state = _state
    return _state


def mk_tar_dir(issuer, test_profile):
    wd = os.getcwd()

    # Make sure there is a tar directory
    tardirname = wd
    for part in ["tar", issuer, test_profile]:
        tardirname = os.path.join(tardirname, part)
        if not os.path.isdir(tardirname):
            os.mkdir(tardirname)

    # Now walk through the log directory and make symlinks from
    # the log files to links in the tar directory
    logdirname = os.path.join(wd, "log", issuer, test_profile)
    for item in os.listdir(logdirname):
        if item.startswith("."):
            continue

        ln = os.path.join(logdirname, item)
        tn = os.path.join(tardirname, "{}.txt".format(item))

        if os.path.isfile(tn):
            os.unlink(tn)

        if not os.path.islink(tn):
            os.symlink(ln, tn)


def create_tar_archive(issuer, test_profile):
    mk_tar_dir(issuer, test_profile)

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
