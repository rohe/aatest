__author__ = 'roland'


class HandlerResponse(object):
    def __init__(self, content_processed, user_action='',
                 cookie_jar=None, http_response=None, response=None):
        """

        :param content_processed: bool
        :param user_action: A string denoting user action ('OK‘, 'NOK’,
        'aborted‘)
        :param cookie_list: A CookieJar instance
        :param http_response: A Response instance
        :param response: A semi parsed response, might be a dictionary
        """
        self.content_processed = content_processed
        self.user_action = user_action
        self.cookie_jar = cookie_jar
        self.http_response = http_response
        self.response = response


class ContentHandler(object):
    def __init__(self):
        pass

    def handle_response(self, **kwargs):
        raise NotImplemented()
