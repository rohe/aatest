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

    def handle_response(self, http_response, auto_close_urls,
                        conv=None, verify_ssl=True, cookie_jar=None):
        """

        :param http_response: The HTTP response to handle
        :param auto_close_urls: A list of URLs that if encountered should
        lead to an immediate break in processing.
        :param conv: A aatest.Conversation instance
        :param verify_ssl: (True/False) whether the ssl certificates must
        be verified. Default is True
        :param cookie_jar: A http.cookiejar.CookieJar instance
        :return: A aatest.contenthandler.HandlerResponse instance
        """
        raise NotImplemented()
