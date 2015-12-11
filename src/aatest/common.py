import logging
from aatest.verify import Verify


def setup_logger(log, log_file_name="tt.log"):
    # logger = logging.getLogger("")
    hdlr = logging.FileHandler(log_file_name)
    base_formatter = logging.Formatter(
        "%(asctime)s %(name)s:%(levelname)s %(message)s")

    hdlr.setFormatter(base_formatter)
    log.addHandler(hdlr)
    log.setLevel(logging.DEBUG)


def make_list(flows, profile, map_prof, **kw_args):
    f_names = list(flows.keys())
    f_names.sort()
    flow_names = []
    for k in kw_args["orddesc"]:
        k += '-'
        l = [z for z in f_names if z.startswith(k)]
        flow_names.extend(l)

    res = []
    if profile:
        sprofile = profile.split(".")
    else:
        sprofile = []

    for tid in flow_names:
        _flow = flows[tid]

        if map_prof(sprofile, _flow["profile"].split(".")):
            res.append(tid)

    return res


def make_entity(**kw_args):
    raise NotImplemented()


def node_dict(flows, lst):
    return dict([(l, flows[l]) for l in lst])


def test_summation(conv, sid):
    status = 0
    for item in conv.events.get('test_output'):
        _item = item.data
        if _item["status"] > status:
            status = _item["status"]

    if status == 0:
        status = 1

    info = {
        "id": sid,
        "status": status,
        "tests": [d.data for d in conv.events.get('test_output')]
    }

    return info


def run_flow(profiles, conv, test_id, conf, profile, chk_factory, index=0):
    print(("==" + test_id))
    conv.test_id = test_id
    conv.conf = conf

    if index >= len(conv.flow["sequence"]):
        return None

    conv.index = index

    for item in conv.flow["sequence"][index:]:
        if isinstance(item, tuple):
            cls, funcs = item
        else:
            cls = item
            funcs = {}

        _oper = cls(conv=conv, profile=profile, test_id=test_id,
                    conf=conf, funcs=funcs, chk_factory=chk_factory)
        conv.operation = _oper
        conv.events.store('operation', _oper)
        _oper.setup(profiles.PROFILEMAP)
        _oper()

        conv.index += 1

    try:
        if conv.flow["tests"]:
            _ver = Verify(chk_factory, conv.msg_factory, conv)
            _ver.test_sequence(conv.flow["tests"])
    except KeyError:
        pass
    except Exception as err:
        raise

    info = test_summation(conv, test_id)

    return info
