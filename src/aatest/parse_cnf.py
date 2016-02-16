import json
import yaml
from aatest import Unknown
from aatest.func import factory as aafactory

__author__ = 'roland'


class MissingParent(Exception):
    pass


def _get_cls(name, factories, use=''):
    if use:
        try:
            cls = factories[use](name)
        except Unknown:
            pass
        else:
            return cls

    try:
        cls = factories[''](name)
    except Unknown:
        raise Exception("Unknown Class: '{}'".format(name))

    return cls


def _get_func(dic, func_factory):
    """
    Convert function names into function references

    :param dic: A key, value dictionary where keys are function names
    :param func_factory: Factory function used to find functions
    :return: A dictionary with the keys replace with references to functions
    """
    res = {}
    for fname, val in dic.items():
        func = func_factory(fname)
        if func is None:
            func = aafactory(fname)

        if func is None:
            raise Exception("Unknown function: '{}'".format(fname))
        res[func] = val

    return res


def parse_yaml_conf(cnf_file, cls_factories, func_factory, use=''):
    """

    :param cnf_file:
    :param use:
    :return:
    """
    stream = open(cnf_file, 'r')
    yc = yaml.safe_load(stream)
    stream.close()
    for tid, spec in yc['Flows'].items():
        seq = []
        for oper in spec["sequence"]:
            if isinstance(oper, dict):  # Must be only one key, value item
                if len(oper) > 1:
                    raise SyntaxError(tid)
                key, val = list(oper.items())[0]
                try:
                    seq.append((_get_cls(key, cls_factories, use),
                                _get_func(val, func_factory)))
                except Exception:
                    print('tid:{}'.format(tid))
                    raise
            else:
                try:
                    seq.append(_get_cls(oper, cls_factories, use))
                except Exception:
                    print('tid:{}'.format(tid))
                    raise
        spec["sequence"] = seq

    return yc


def parse_json_conf(cnf_file, cls_factories, func_factory, use=''):
    """

    :param cnf_file:
    :param use:
    :return:
    """
    stream = open(cnf_file, 'r')
    js = json.load(stream)
    stream.close()
    for tid, spec in js['Flows'].items():
        seq = []
        for oper in spec["sequence"]:
            if isinstance(oper, dict):  # Must be only one key, value item
                if len(oper) > 1:
                    raise SyntaxError(tid)
                key, val = list(oper.items())[0]
                try:
                    seq.append((_get_cls(key, cls_factories, use),
                                _get_func(val, func_factory)))
                except Exception:
                    print('tid:{}'.format(tid))
                    raise
            else:
                try:
                    seq.append(_get_cls(oper, cls_factories, use))
                except Exception:
                    print('tid:{}'.format(tid))
                    raise
        spec["sequence"] = seq

    return js


class Item(object):
    def __init__(self, parent, name, desc):
        self.parent = parent
        self.desc = desc
        self.name = name
        self.child = []


def build_hierarchy(flows):
    items = {}

    for id, desc in flows.items():
        items[id] = Item('', id, desc)

    for item in items.values():
        try:
            _pre = item.desc['super']
        except KeyError:
            continue
        else:
            try:
                _parent = items[_pre]
                _parent.child.append(item)
                item.parent = _parent
            except KeyError:
                raise MissingParent(item.desc['super'])

    return items


def flatten(interim):
    res = []
    for f in interim:
        res.append(f)
        if f.child:
            res.extend(flatten(sorted(f.child, key=lambda x: x.name)))
    return res


def sort(display_order, flows):
    items = build_hierarchy(flows)
    # toplevel
    f_names = [f for f in items.values() if not f.parent]
    interim = []
    for k in display_order:
        k += '-'
        l = [z for z in f_names if z.name.startswith(k)]
        interim.extend(sorted(l, key=lambda x: x.name))

    return flatten(interim)
