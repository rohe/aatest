from aatest.time_util import in_a_while

__author__ = 'roland'


class ProfileHandler(object):
    def __init__(self, session):
        self.session = session

    def to_profile(self, representation="list"):
        return None

    def get_profile_info(self, test_id=None):
        try:
            _conv = self.session["conv"]
        except KeyError:
            pass
        else:
            try:
                iss = _conv.client.provider_info["issuer"]
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