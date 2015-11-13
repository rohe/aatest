import json
import re

from urllib.parse import urlparse
from robobrowser import RoboBrowser

NO_CTRL = "No submit control with the name='%s' and value='%s' could be found"


class FlowException(Exception):
    def __init__(self, function="", content="", url=""):
        Exception.__init__(self)
        self.function = function
        self.content = content
        self.url = url

    def __str__(self):
        return json.dumps(self.__dict__)


class InteractionNeeded(Exception):
    pass


def no_func():
    return None


class RResponse():
    """
    A Response class that behaves in the way that mechanize expects it.
    Links to a requests.Response
    """
    def __init__(self, resp):
        self._resp = resp
        self.index = 0
        self.text = resp.text
        if isinstance(self.text, str):
            if resp.encoding.upper() == "UTF-8":
                self.text = self.text.encode("utf-8")
            else:
                self.text = self.text.encode("latin-1")
        self._len = len(self.text)
        self.url = str(resp.url)
        self.statuscode = resp.status_code

    def geturl(self):
        return self._resp.url

    def __getitem__(self, item):
        try:
            return getattr(self._resp, item)
        except AttributeError:
            return getattr(self._resp.headers, item)

    def __getattribute__(self, item):
        try:
            return getattr(self._resp, item)
        except AttributeError:
            return getattr(self._resp.headers, item)

    def read(self, size=0):
        """
        Read from the content of the response. The class remembers what has
        been read so it's possible to read small consecutive parts of the
        content.

        :param size: The number of bytes to read
        :return: Somewhere between zero and 'size' number of bytes depending
            on how much it left in the content buffer to read.
        """
        if size:
            if self._len < size:
                return self.text
            else:
                if self._len == self.index:
                    part = None
                elif self._len - self.index < size:
                    part = self.text[self.index:]
                    self.index = self._len
                else:
                    part = self.text[self.index:self.index + size]
                    self.index += size
                return part
        else:
            return self.text


class Interaction(object):
    def __init__(self, httpc, interactions=None, verify_ssl=True):
        self.httpc = httpc
        self.browser = RoboBrowser()
        self.interactions = interactions
        self.verify_ssl = verify_ssl

    def pick_interaction(self, response, base):
        if self.interactions is None:
            return None

        self.browser._update_state(response)
        _bs = self.browser.parsed
        unic = ""

        for interaction in self.interactions:
            _match = 0
            for attr, val in list(interaction["matches"].items()):
                if attr == "url":
                    if val == base:
                        _match += 1
                elif attr == "title":
                    if _bs is None:
                        break
                    if _bs.title is None:
                        break
                    if val in _bs.title.contents:
                        _match += 1
                    else:
                        _c = _bs.title.contents
                        if isinstance(_c, list) and not isinstance(_c, str):
                            for _line in _c:
                                if val in _line:
                                    _match += 1
                                    continue
                elif attr == "content":
                    if unic and val in unic:
                        _match += 1

            if _match == len(interaction["matches"]):
                return interaction

        raise InteractionNeeded("No interaction matched")

    def pick_form(self, forms, **kwargs):
        """
        Picks which form in a web-page that should be used

        :param forms: A list of robobrowser.Forms instances
        :return: The picked form or None if no form matched the criteria.
        """

        _form = None

        if len(forms) == 1:
            _form = forms[0]
        else:
            if "pick" in kwargs:
                _dict = kwargs["pick"]
                for form in forms:
                    if _form:
                        break
                    for key, _ava in list(_dict.items()):
                        if key == "form":
                            _keys = list(form.attrs.keys())
                            for attr, val in list(_ava.items()):
                                if attr in _keys and val == form.attrs[attr]:
                                    _form = form
                        elif key == "control":
                            prop = _ava["id"]
                            _default = _ava["value"]
                            try:
                                orig_val = form[prop]
                                if isinstance(orig_val, str):
                                    if orig_val == _default:
                                        _form = form
                                elif _default in orig_val:
                                    _form = form
                            except KeyError:
                                pass
                            except Exception as err:
                                pass
                        elif key == "method":
                            if form.method == _ava:
                                _form = form
                        else:
                            _form = None

                        if not _form:
                            break
            elif "index" in kwargs:
                _form = forms[int(kwargs["index"])]

        return _form

    # def do_click(self, form, **kwargs):
    #     """
    #     Emulates the user clicking submit on a form.
    #
    #     :param form: The form that should be submitted
    #     :return: What do_request() returns
    #     """
    #
    #     if "click" in kwargs:
    #         request = None
    #         _name = kwargs["click"]
    #         try:
    #             _ = form.find_control(name=_name)
    #             request = form.click(name=_name)
    #         except AmbiguityError:
    #             # more than one control with that name
    #             _val = kwargs["set"][_name]
    #             _nr = 0
    #             while True:
    #                 try:
    #                     cntrl = form.find_control(name=_name, nr=_nr)
    #                     if cntrl.value == _val:
    #                         request = form.click(name=_name, nr=_nr)
    #                         break
    #                     else:
    #                         _nr += 1
    #                 except ControlNotFoundError:
    #                     raise Exception(NO_CTRL % (_name, _val))
    #     else:
    #         request = form.click()
    #
    #     headers = {"Referer": kwargs["location"]}
    #
    #     for key, val in list(request.unredirected_hdrs.items()):
    #         headers[key] = val
    #
    #     url = request._Request__original
    #
    #     if form.method == "POST":
    #         return self.httpc.send(url, "POST", data=request.data,
    #                                headers=headers)
    #     else:
    #         return self.httpc.send(url, "GET", headers=headers)

    def select_form(self, response, **kwargs):
        """
        Pick a form on a web page, possibly enter some information and submit
        the form.

        :param orig_response: The original response (as returned by requests)
        :return: The response do_click() returns
        """
        self.browser._update_state(response)
        forms = self.browser.get_forms()
        form = self.pick_form(forms, **kwargs)

        if not forms:
            raise Exception("Can't pick a form !!")

        if "set" in kwargs:
            for key, val in list(kwargs["set"].items()):
                if key.startswith("_"):
                    continue
                if "click" in kwargs and kwargs["click"] == key:
                    continue

                try:
                    form[key].value = val
                except (ValueError):
                    pass
                except Exception as err:
                    raise
                    # cntrl = form.find_control(key)
                    # if isinstance(cntrl, ListControl):
                    #     form[key] = [val]
                    # else:
                    #     raise

        if form.action in kwargs["tester"].my_endpoints():
            _res = {}
            for name, cnt in form.fields.items():
                _res[name] = cnt.value
            return _res

        try:
            requests_args = kwargs["requests_args"]
        except KeyError:
            requests_args = {}

        self.browser.submit_form(form, **requests_args)
        return self.browser.state.response

    #noinspection PyUnusedLocal
    def chose(self, orig_response, path, **kwargs):
        """
        Sends a HTTP GET to a url given by the present url and the given
        relative path.

        :param orig_response: The original response
        :param content: The content of the response
        :param path: The relative path to add to the base URL
        :return: The response do_click() returns
        """

        try:
            _trace = kwargs["trace"]
        except KeyError:
            _trace = False

        if not path.startswith("http"):
            try:
                _url = orig_response.url
            except KeyError:
                _url = kwargs["location"]

            part = urlparse(_url)
            url = "%s://%s%s" % (part[0], part[1], path)
        else:
            url = path

        return self.httpc.send(url, "GET", trace=_trace)
        #return resp, ""

    def redirect(self, orig_response, url_regex, **kwargs):
        """
        Simulates a JavaScript redirect by extracting the target of the
        redirection from the page content using the given regex

        :param orig_response: The original response
        :param url_regex: The regex that defines how the target of the redirect
                          can be extracted from the content
        """

        matches = re.findall(url_regex, orig_response.content)
        no_of_matches = len(matches)
        if not no_of_matches == 1:
            raise InteractionNeeded("Expected single match but found %d",
                                    no_of_matches)

        url = matches[0]
        return self.httpc.send(url, "GET")

    def post_form(self, response, **kwargs):
        """
        The same as select_form but with no possibility of changing the content
        of the form.

        :param response: The original response (as returned by requests)
        :return: The response submit_form() returns
        """

        form = self.pick_form(response, **kwargs)

        return self.browser.submit_form(form)


    #noinspection PyUnusedLocal
    def interaction(self, args):
        _type = args["type"]
        if _type == "form":
            return self.select_form
        elif _type == "link":
            return self.chose
        #elif _type == "response":
        #    return self.parse
        elif _type == "redirect":
            return self.redirect
        elif _type == "javascript_redirect":
            return self.redirect
        else:
            return no_func

# ========================================================================


class Action(object):
    def __init__(self, args):
        self.args = args or {}
        self.request = None

    def update(self, dic):
        self.args.update(dic)

    #noinspection PyUnusedLocal
    def post_op(self, result, conv, args):
        pass

    def __call__(self, tester, location, response, features, **kwargs):
        _conv = tester.conv
        intact = _conv.interaction
        function = intact.interaction(self.args)

        try:
            _args = self.args.copy()
        except (KeyError, AttributeError):
            _args = {}

        _args["_trace_"] = _conv.trace
        _args["location"] = location
        _args["features"] = features
        _args["tester"] = tester
        _args["requests_args"] = kwargs

        if _conv.trace:
            _conv.trace.reply("FUNCTION: %s" % function.__name__)
            _conv.trace.reply("ARGS: %s" % _args)

        result = function(response, **_args)
        self.post_op(result, _conv, _args)
        return result
