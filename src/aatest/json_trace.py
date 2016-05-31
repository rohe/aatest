import json
import time


class JTrace(object):
    def __init__(self, absolut_start=False):
        self.trace = []
        self.start = time.time()
        if absolut_start:
            self.trace.append(
                {"init": time.strftime(
                        "%a, %d %b %Y %H:%M:%S +0000", time.gmtime())})

    @staticmethod
    def format(resp):
        raise NotImplemented()

    def request(self, msg):
        self.trace.append({"delta": time.time() - self.start, "request": msg})

    def reply(self, msg):
        self.trace.append({"delta": time.time() - self.start, "reply": msg})

    def response(self, resp):
        raise NotImplemented()

    def info(self, msg):
        self.trace.append({"delta": time.time() - self.start, "info": msg})

    def error(self, msg):
        self.trace.append({"delta": time.time() - self.start, "error": msg})

    def warning(self, msg):
        self.trace.append({"delta": time.time() - self.start, "warning": msg})

    def _str(self, item):
        return json.dumps(item, indent=2, sort_keys=True)

    def __str__(self):
        return "\n".join([self._str(t) for t in self.trace])

    def clear(self):
        self.trace = []

    def __next__(self):
        for line in self.trace:
            yield line

    def lastline(self):
        try:
            return self.trace[-1]
        except IndexError:
            return ""
