from aatest import func
from aatest import operation
from aatest.session import SessionHandler
from aatest.parse_cnf import parse_json_conf

__author__ = 'roland'


def test_session_init():
    factories = {'': operation.factory}
    cnf = parse_json_conf('flows.json', factories, func.factory)
    kwargs = {'profile': None, 'flows': cnf['Flows'], 'order': cnf['Order']}
    sh = SessionHandler(session={}, **kwargs)
    session = sh.init_session(sh.session, profile=kwargs['profile'])

    assert session['flow_names'] == ['AA-Dummy-Default-1', 'AA-Dummy-B',
                                     'AA-Dummy-A']
    assert len(session['tests']) == 3