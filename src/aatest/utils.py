import logging
import os
import tarfile


def setup_logging(logfile, log):
    hdlr = logging.FileHandler(logfile)
    base_formatter = logging.Formatter(
        "%(asctime)s %(name)s:%(levelname)s %(message)s")

    hdlr.setFormatter(base_formatter)
    log.addHandler(hdlr)
    log.setLevel(logging.DEBUG)


def not_logging(logfile, logger):
    hdlr = logging.FileHandler(logfile)
    base_formatter = logging.Formatter(
        "%(asctime)s %(name)s:%(levelname)s %(message)s")

    hdlr.setFormatter(base_formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.DEBUG)


def get_test_info(session, test_id):
    return session["test_info"][test_id]