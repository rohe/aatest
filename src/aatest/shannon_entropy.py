from future.backports import ceil
from math import log

__author__ = 'roland'


def hist(source):
    hist = {}
    l = 0
    for e in source:
        l += 1
        if e not in hist:
            hist[e] = 0
        hist[e] += 1
    return (l, hist)


def entropy(hist, l):
    elist = []
    for v in hist.values():
        c = v / l
        elist.append(-c * log(c, 2))
    return sum(elist)


def calculate(source):
    (l, h) = hist(source)
    return l * ceil(entropy(h, l))


if __name__ == '__main__':
    print(calculate('InAGkrHTT7Yz1gDk'))