from aatest.time_util import in_a_while

__author__ = 'roland'


class ProfileHandler(object):
    def __init__(self, session):
        self.session = session

    def to_profile(self, representation="list"):
        return None

    def get_profile_info(self, test_id=None):
        return {}