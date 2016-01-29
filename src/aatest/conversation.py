import logging
from aatest.interaction import Interaction
from aatest import Trace
from aatest.events import Events

__author__ = 'roland'

logger = logging.getLogger(__name__)


class Conversation(object):
    def __init__(self, flow, entity, msg_factory, check_factory=None,
                 features=None, trace_cls=Trace, interaction=None,
                 **extra_args):
        self.flow = flow
        self.entity = entity
        self.msg_factory = msg_factory
        self.trace = trace_cls(True)
        self.events = Events()
        self.interaction = Interaction(self.entity, interaction)
        self.check_factory = check_factory
        self.features = features
        self.extra_args = extra_args
        self.test_id = ""
        self.info = {}
        self.index = 0
        self.comhandler = None
        self.exception = None
        self.sequence = []
        self.trace.info('Conversation initiated')
        self.cache = {}
