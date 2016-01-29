__author__ = 'roland'


class HandlerResponse(object):
    def __init__(self, content_processed, outside_html_action=None,
                 tester_error_description=None,
                 cookie_jar=None, http_response=None, response=None):
        """

        :param content_processed: bool set to True if a scripted ContentHandler
        matches and processes a page; If False then the next ContentHandler
        must take over
        :param user_action: A string denoting user action ('OK‘, 'NOK’,
        'aborted‘) outside the HTML page.
        :param cookie_list: A CookieJar instance
        :param http_response: A Response instance
        :param outside_html_action: Value from outside_html_actions or None
        :param tester_error_description: optional text if outside_html_action
        is not None
        :param response: A semi parsed response, might be a dictionary
        """
        self.content_processed = content_processed
        self.outside_html_action = outside_html_action
        self.cookie_jar = cookie_jar
        self.http_response = http_response
        self.response = response
        self.tester_error_description = tester_error_description


class ContentHandler(object):
    """
    Process the HTML contents of a response from the test target. This can
    either be a scripted approach, or invoke a browser.
    """

    def __init__(self):
        pass

    def handle_response(self, http_response, auto_close_urls,
                        conv=None, verify_ssl=True, cookie_jar=None,
                        outside_html_actions=None):
        """

        :param http_response: The HTTP response to handle
        :param auto_close_urls: A list of URLs that if encountered should
        lead to an immediate break in processing, like a form action. Other
        URLs in the page will load local resources such as css and js without
        returning control.
        :param conv: A aatest.Conversation instance
        :param verify_ssl: (True/False) whether the ssl certificates must
        be verified. Default is True
        :param cookie_jar: A http.cookiejar.CookieJar instance
        :param outside_html_actions: a dict describing buttons for the widget
        outside the html-area, to be used if the test must be aborted
        :return: A aatest.contenthandler.HandlerResponse instance
        """
        raise NotImplemented()
