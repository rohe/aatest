from aatest import END_TAG
from aatest.check import STATUSCODE, WARNING, CRITICAL

__author__ = 'roland'

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


def represent_result(info, tid):
    if not end_tags(info):
        return "PARTIAL RESULT"

    _stat = test_summation(info["test_output"], tid)["status"]

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

    if text == "PASSED":
        try:
            text = "UNKNOWN - %s" % info["node"].kwargs["result"]
        except KeyError:
            pass

    if warnings:
        text = "%s\nWarnings:\n%s" % (text, "\n".join(warnings))

    return text
