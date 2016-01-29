from aatest import func
from aatest import operation
from aatest.yamlcnf import parse_yaml_conf

__author__ = 'roland'


def test_parse_yaml_conf():
    factories = {'': operation.factory}
    cnf = parse_yaml_conf('flows.yaml', factories, func.factory)

    assert cnf

    assert cnf['Desc'] == {'Default': 'Default settings'}
    assert list(cnf['Flows'].keys()) == ['AA-Dummy-Default-1']
    assert cnf['Order'] == ['AA-Dummy-Default']