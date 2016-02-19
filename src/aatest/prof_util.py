import os

from aatest.time_util import in_a_while
from future.backports.urllib.parse import quote_plus

from aatest.log import with_or_without_slash

__author__ = 'roland'


class ProfileHandler(object):
    def __init__(self, session):
        self.session = session

    def to_profile(self, representation="list"):
        return []

    def get_profile_info(self, test_id=None):
        try:
            _conv = self.session["conv"]
        except KeyError:
            pass
        else:
            try:
                iss = _conv.entity.provider_info["issuer"]
            except TypeError:
                iss = ""

            profile = self.to_profile("dict")

            if test_id is None:
                try:
                    test_id = self.session["testid"]
                except KeyError:
                    return {}

            return {"Issuer": iss, "Profile": profile,
                    "Test ID": test_id,
                    "Test description": self.session["node"].desc,
                    "Timestamp": in_a_while()}

        return {}

    def log_path(self, test_id=None):
        _conv = self.session["conv"]

        try:
            iss = _conv.entity.provider_info["issuer"]
        except (TypeError, KeyError):
            return ""
        else:
            qiss = quote_plus(iss)

        path = with_or_without_slash(os.path.join("log", qiss))
        if path is None:
            path = os.path.join("log", qiss)

        prof = ".".join(self.to_profile())

        if not os.path.isdir("{}/{}".format(path, prof)):
            os.makedirs("{}/{}".format(path, prof))

        if test_id is None:
            test_id = self.session["testid"]

        return "{}/{}/{}".format(path, prof, test_id)