from datetime import datetime
from datetime import timedelta

__author__ = 'roland'

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def time_in_a_while(days=0, seconds=0, microseconds=0, milliseconds=0,
                    minutes=0, hours=0, weeks=0):
    """
    format of timedelta:
        timedelta([days[, seconds[, microseconds[, milliseconds[,
                    minutes[, hours[, weeks]]]]]]])
    :return: UTC time
    """
    delta = timedelta(days, seconds, microseconds, milliseconds,
                      minutes, hours, weeks)
    return datetime.utcnow() + delta


def in_a_while(days=0, seconds=0, microseconds=0, milliseconds=0,
               minutes=0, hours=0, weeks=0, time_format=TIME_FORMAT):
    """
    format of timedelta:
        timedelta([days[, seconds[, microseconds[, milliseconds[,
                    minutes[, hours[, weeks]]]]]]])
    """
    if time_format is None:
        time_format = TIME_FORMAT

    return time_in_a_while(days, seconds, microseconds, milliseconds,
                           minutes, hours, weeks).strftime(time_format)


