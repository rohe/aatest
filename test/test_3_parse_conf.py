from aatest import func
from aatest import operation
from aatest.parse_cnf import parse_json_conf
from aatest.parse_cnf import parse_yaml_conf
from aatest.parse_cnf import sort

__author__ = 'roland'


def _eq(l1, l2):
    return set(l1) == set(l2)


def test_parse_yaml_conf():
    factories = {'': operation.factory}
    cnf = parse_yaml_conf('flows.yaml', factories, func.factory)

    assert cnf

    assert cnf['Desc'] == {'Default': 'Default settings'}
    assert list(cnf['Flows'].keys()) == ['AA-Dummy-Default-1']
    assert cnf['Order'] == ['AA-Dummy-Default']


def test_parse_json_conf():
    factories = {'': operation.factory}
    cnf = parse_json_conf('flows.json', factories, func.factory)

    assert cnf

    assert cnf['Desc'] == {'Default': 'Default settings'}
    assert _eq(list(cnf['Flows'].keys()),
               ['AA-Dummy-Default-1', 'AA-Dummy-A', 'AA-Dummy-B'])
    assert cnf['Order'] == ['AA-Dummy']


def test_sort():
    factories = {'': operation.factory}
    cnf = parse_json_conf('flows.json', factories, func.factory)

    flows = sort(cnf['Order'], cnf['Flows'])

    assert [f.name for f in flows] == ['AA-Dummy-Default-1', 'AA-Dummy-B',
                                       'AA-Dummy-A']