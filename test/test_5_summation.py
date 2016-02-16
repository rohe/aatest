from aatest import END_TAG
from aatest import func
from aatest import operation

from aatest.check import OK
from aatest.check import WARNING
from aatest.check import ERROR
from aatest.check import CRITICAL
from aatest.check import State
from aatest.events import Events
from aatest.events import EV_CONDITION
from aatest.session import SessionHandler
from aatest.summation import completed
from aatest.summation import represent_result
from aatest.summation import eval_state
from aatest.parse_cnf import parse_yaml_conf

__author__ = 'roland'

EVENT_SEQUENCE = [
   [EV_CONDITION, State('1', OK)],
   [EV_CONDITION, State('2', OK)],
   [EV_CONDITION, State('3', OK)],
   [EV_CONDITION, State('4', OK)],
   [EV_CONDITION, State('5', OK)],
]


def test_completed():
    events = Events()
    for event in EVENT_SEQUENCE:
        events.store(*event)

    assert completed(events) is False

    events.store(EV_CONDITION, State(END_TAG, status=OK))

    assert completed(events) is True


def test_eval_state():
    events = Events()
    events.store(EV_CONDITION, State('1', OK))
    events.store(EV_CONDITION, State('2', WARNING, message='Stumbled'))

    assert eval_state(events) == WARNING

    events.store(EV_CONDITION, State('3', ERROR, message="Shouldn't be"))

    assert eval_state(events) == ERROR

    events.store(EV_CONDITION, State('4', CRITICAL, message="Hands off"))

    assert eval_state(events) == CRITICAL


def test_represent_result():
    events = Events()
    events.store(EV_CONDITION, State('1', OK))
    events.store(EV_CONDITION, State(END_TAG, status=OK))

    text = represent_result(events)
    assert text == 'PASSED'

    events = Events()
    events.store(EV_CONDITION, State('1', OK))
    events.store(EV_CONDITION, State('2', WARNING, message='Stumbled'))
    events.store(EV_CONDITION, State(END_TAG, status=OK))

    text = represent_result(events)
    assert text == 'WARNING\nWarnings:\nStumbled'


def test_store_test_state():
    factories = {'': operation.factory}
    cnf = parse_yaml_conf('flows.yaml', factories, func.factory)
    kwargs = {'profile': None, 'flows': cnf['Flows'], 'order': cnf['Order']}
    sh = SessionHandler(session={}, **kwargs)
    session = sh.init_session(sh.session, profile=kwargs['profile'])
