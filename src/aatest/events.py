import time

__author__ = 'roland'

# Message direction
INCOMING = 1
OUTGOING = 2

# standard event labels
EV_CONDITION = 'condition'
EV_EXCEPTION = 'exception'
EV_FAULT = 'fault'
EV_HANDLER_RESPONSE = 'handler response'
EV_HTML_SRC = 'html_src'
EV_HTTP_ARGS = 'http args'
EV_HTTP_INFO = 'http info'
EV_HTTP_RESPONSE = 'http response'
EV_HTTP_RESPONSE_HEADER = 'http response header'
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


class HTTPResponse(object):
    def __init__(self, response):
        try:
            self.status_code = response.status_code
        except AttributeError:
            self.status_code = int(response.status.split(' ')[0])
        try:
            self.url = response.url
        except AttributeError:
            self.url = ''

        self.headers = response.headers

        # Should perhaps be more intelligent about this
        if self.status_code >= 400:
            try:
                self.text = response.text
            except AttributeError:
                self.text = response.message
        else:
            self.text = ''


class Event(object):
    def __init__(self, timestamp=0, typ='', data=None, ref='', sub='',
                 sender='', direction=0):
        self.timestamp = timestamp or time.time()
        self.typ = typ
        self.data = data
        self.ref = ref
        self.sub = sub
        self.sender = sender
        self.direction = direction

    def __str__(self):
        return '{}:{}:{}'.format(self.timestamp, self.typ, self.data)

    def __eq__(self, other):
        if isinstance(other, Event):
            for param in ['timestamp', 'typ', 'data', 'ref', 'sub', 'sender']:
                if getattr(self, param) != getattr(other, param):
                    return False
        return True

    def older(self, other):
        if other.timestamp >= self.timestamp:
            return True
        return False


class Events(object):
    def __init__(self):
        self.events = []

    def store(self, typ, data, ref='', sub='', sender='', direction=0):
        index = time.time()

        if typ == EV_HTTP_RESPONSE:  # only store part of the instance
            data = HTTPResponse(data)

        self.events.append(Event(index, typ, data, ref, sub, sender, direction))
        return index

    def by_index(self, index):
        l = [e for e in self.events if e.timestamp == index]
        if l:
            return l[0]
        else:
            raise KeyError(index)

    def by_ref(self, ref):
        return [e for e in self.events if e.ref == ref]

    def by_direction(self, direction):
        return [e for e in self.events if e.direction == direction]

    def get(self, typ):
        return [ev for ev in self.events if ev.typ == typ]

    def get_data(self, typ, sender=''):
        if sender:
            return [d.data for d in self.get(typ) if d.sender == sender]
        else:
            return [d.data for d in self.get(typ)]

    def get_messages(self, typ, msg_cls):
        res = []
        for m in self.get(typ):
            if m.data.__class__ == msg_cls:
                res.append(m.data)
        #return [m.data for m in self.get(typ) if isinstance(m.data, msg_cls)]
        return res

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

    def __contains__(self, event):
        ts = event.timestamp
        for ev in self.events:
            if event.timestamp == ev.timestamp:
                if event == ev:
                    return True

        return False

    def sort(self):
        self.events.sort(key=lambda event: event.timestamp)

    def to_html(self, form='table'):
        if form == 'list':
            text = ['<ul>']
            for ev in self.events:
                text.append('<li> {}'.format(ev))
            text.append('</ul>')
        else:
            text = ['<table border=1>']
            for ev in self.events:
                text.append(
                    '<tr><td>{time}</td><td>{typ}</td><td>{data}</td></tr>'.format(
                        time=ev.timestamp, typ=ev.typ, data=ev.data))
            text.append('</table>')

        return '\n'.join(text)

    def __str__(self):
        return '\n'.join(['{}'.format(ev) for ev in self.events])

    def reset(self):
        self.events = []

    def when(self, typ, msg):
        res = []
        for m in self.get(typ):
            if m.data.__class__ == msg:
                res.append(m.timestamp)

        return res

    def last_event_type(self):
        return self.events[-1].typ