import time

__author__ = 'roland'

# standard event labels
EV_CONDITION = 'condition'
EV_FAULT = 'fault'
EV_HTTP_ARGS = 'http args'
EV_HTTP_RESPONSE = 'http response'
EV_OPERATION = 'operation'
EV_PROTOCOL_RESPONSE = 'protocol response'
EV_PROTOCOL_REQUEST = 'protocol request'
EV_REDIRECT_URL = 'redirect url'
EV_REPLY = 'reply'
EV_REQUEST = 'request'
EV_REQUEST_ARGS = 'request args'
EV_RESPONSE = 'response'
EV_RESPONSE_ARGS = 'response args'
EV_SEND = 'send'
EV_URL = 'url'


class NoSuchEvent(Exception):
    pass


class Event(object):
    def __init__(self, timestamp=0, typ='', data=None, ref='', sub=''):
        self.timestamp = timestamp
        self.typ = typ
        self.data = data
        self.ref = ref
        self.sub = sub

    def __str__(self):
        return '{}:{}:{}'.format(self.timestamp, self.typ, self.data)


class Events(object):
    def __init__(self):
        self.events = []

    def store(self, typ, data, ref=''):
        index = time.time()
        self.events.append(Event(index, typ, data, ref))
        return index

    def by_index(self, index):
        l = [e for e in self.events if e.timestamp == index]
        if l:
            return l[0]
        else:
            raise KeyError(index)

    def by_ref(self, ref):
        return [e for e in self.events if e.ref == ref]

    def get(self, typ):
        return [ev for ev in self.events if ev.typ == typ]

    def get_data(self, typ):
        return [d.data for d in self.get(typ)]

    def get_messages(self, typ, msg_cls):
        return [m.data for m in self.get(typ) if isinstance(m.data, msg_cls)]

    def last(self, typ):
        res = self.get(typ)
        if len(res):
            return res[-1]
        else:
            return None

    def get_message(self, typ, msg_cls):
        l = self.get_messages(typ, msg_cls)
        if l:
            return l[-1]

        raise NoSuchEvent('{}:{}'.format(typ, msg_cls))

    def last_item(self, typ):
        l = self.get_data(typ)
        if l:
            return l[-1]

        raise NoSuchEvent(typ)

    def __len__(self):
        return len(self.events)

    def __getitem__(self, item):
        return self.get_data(item)

    def __setitem__(self, key, value):
        self.store(key, value)

    def append(self, event):
        assert isinstance(event, Event)
        self.events.append(event)

    def extend(self, events):
        for event in events:
            self.append(event)

    def __iter__(self):
        return self.events.__iter__()

    def last_of(self, types):
        l = self.events[:]
        l.reverse()
        for ev in l:
            if ev.typ in types:
                return ev.data

        return None
