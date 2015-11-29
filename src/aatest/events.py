import time

__author__ = 'roland'

class NoSuchEvent(Exception):
    pass


class Event(object):
    def __init__(self, timestamp=0, typ='', data=None):
        self.timestamp = timestamp
        self.typ = typ
        self.data = data

    def __str__(self):
        return '{}:{}:{}'.format(self.timestamp, self.typ, self.data)


class Events(object):
    def __init__(self):
        self.events = []

    def store(self, typ, data):
        self.events.append(Event(time.time(), typ, data))

    def get(self, typ):
        res = []
        for ev in self.events:
            if ev.typ == typ:
                res.append(ev)
        return res

    def last(self, typ):
        res = self.get(typ)
        if len(res):
            return res[-1]
        else:
            return None

    def get_message(self, typ, msg_cls):
        for ev in reversed(self.get(typ)):
            if isinstance(ev.data, msg_cls):
                return ev.data
        return None

    def get_data(self, typ):
        return [d.data for d in self.get(typ)]

    def last_item(self, typ):
        ev = self.last(typ)
        if ev:
            return ev.data

        raise NoSuchEvent(typ)

    def __len__(self):
        return len(self.events)

    def __iter__(self):
        for ev in self.events:
            yield ev