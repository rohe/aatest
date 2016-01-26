import logging
from aatest import FatalError
from aatest.contenthandler import HandlerResponse

__author__ = 'roland'

logger = logging.getLogger(__name__)


class ComHandler(object):
    def __init__(self, contenthandlers, conv=None, auto_close_urls=None):
        self.content_handlers = contenthandlers
        self.conv = conv
        self.auto_close_urls = auto_close_urls or []
        self.verify_ssl = True

    def __call__(self, http_response, target_url='', auto_close_urls=None,
                 conv=None, **kwargs):
        if not http_response:
            return

        auto_close_urls = auto_close_urls or []
        auto_close_urls.extend(self.auto_close_urls)
        rdseq = []

        while True:
            if http_response.status_code >= 400:
                return http_response

            while http_response.status_code in [300,301,302]:
                url = http_response.headers["location"]
                if url in rdseq:
                    raise FatalError("Loop detected in redirects")
                else:
                    rdseq.append(url)
                    if len(rdseq) > 8:
                        raise FatalError(
                            "Too long sequence of redirects: %s" % rdseq)

                logger.info("HTTP %d Location: %s" % (http_response.status_code,
                                                      url))

                if url in auto_close_urls:
                    return http_response

                try:
                    logger.info("GET %s" % url)
                    http_response = self.conv.entity.send(url, "GET")
                except Exception as err:
                    raise FatalError("%s" % err)

                self.conv.events('http response', http_response)

                if http_response.status_code >= 400:
                    return http_response

            handled = False
            for ct in self.content_handlers:
                resp = ct.handle_response(http_response, auto_close_urls,
                                          target_url, conv=self.conv,
                                          verify_ssl=self.verify_ssl,
                                          cookie_jar=self.conv.entity.cookiejar)
                if resp.content_processed:
                    if resp.cookie_jar:
                        self.conv.entity.cookie_jar = resp.cookie_jar
                    if resp.http_response:
                        http_response = resp.http_response
                    else:
                        return resp
                    handled = True
                    break

            if not handled:
                return HandlerResponse(False)
