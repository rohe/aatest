import json
import os
import tarfile
from aatest import END_TAG
from aatest.check import STATUSCODE
from aatest.check import WARNING
from aatest.check import INCOMPLETE
from aatest.check import OK
from aatest.events import EV_CONDITION

__author__ = 'roland'


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


def completed(events):
    """
    Figure out if the test ran to completion
    :param events: An aatest.events.Events instance
    :return: True/False
    """
    for item in events.get_data(EV_CONDITION):
        if item.test_id == END_TAG and item.status == OK:
            return True

    return False


def eval_state(events):
    """
    The state of the test is the equalt to the worst status encountered
    :param events: An aatest.events.Events instance
    :return: An integer representing a status code
    """
    res = OK
    for state in events.get_data(EV_CONDITION):
        if state.status > res:
            res = state.status

    return res


def represent_result(events):
    """
    A textual representation of the status of the test result
    :param events: An aatest.events.Events instance
    :return: A text string
    """
    _state = eval_state(events)
    if not completed(events):
        tag = "PARTIAL RESULT"
    else:
        if _state < WARNING:
            tag = "PASSED"
        elif _state == INCOMPLETE:
            tag = "PARTIAL RESULT"
        else:
            tag = STATUSCODE[_state]

    info = []
    for state in events.get_data(EV_CONDITION):
        if state.status == WARNING:
            if state.message:
                info.append(state.message)

    if info:
        text = "%s\nWarnings:\n%s" % (tag, "\n".join(info))
    else:
        text = tag

    return text


def store_test_state(session, events):
    _node = session['node']
    _node.complete = completed(events)

    _state = eval_state(events)
    if _node.complete:
        _node.state = _state

    return _state


# -----------------------------------------------------------------------------

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
    for cond in events.get_data(EV_CONDITION):
        element.append('{}'.format(cond))
    if html:
        element.append("</code></pre>")
        return "\n".join(element)
    else:
        element.append("\n")
        return element


def pprint_json(json_txt):
    _jso = json.loads(json_txt)
    return json.dumps(_jso, sort_keys=True, indent=2, separators=(',', ': '))


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
