import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Comment
from flask import Flask, Response, request
from requests import get

app = Flask('__main__')
SITE_NAME = 'https://habr.com'
PORT = 1234
TM = '™'


def __replace_path(bs: BeautifulSoup, site: str) -> None:
    """
    Replace path in links href/src attribute

    Receives BS instance and simply replaces string in attributes
    :param bs: BeautifulSoup instance
    :param site: str. Url
    :return: None
    """
    def _replace_attr(attr: str) -> None:
        for link in bs.find_all(**{attr: True}):
            if attr in link.attrs:
                if link[attr].startswith('//'):
                    continue
                elif link[attr].startswith('/'):
                    start = site
                else:
                    start = ''
                link.attrs[attr] = ''.join(('?', start, link.attrs[attr]))

    for attr_name in ('href', 'src'):
        _replace_attr(attr_name)


def __add_tm(bs: BeautifulSoup) -> None:
    """
    Add trademark to six-letter words

    Receives BS instance, trying to find all text elements
    and call the replacement function
    :param bs: BeautifulSoup
    :return: None
    """

    def _el_filter(element):
        if element.parent.name in ['style', 'script', 'head',
                                   'title', 'meta', '[document]']:
            return False
        if isinstance(element, Comment):
            return False
        return True

    for el in filter(_el_filter, bs.find_all(text=True)):
        text = str(el)
        text = re.sub(r'\b(?P<target>\w{6})\b', r'\g<1>' + TM, text)
        el.replace_with(text)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def quasi_proxy(path):
    try:
        if request.query_string:
            path = request.query_string
        response = get(path)
    except (UnicodeDecodeError,
            requests.exceptions.MissingSchema):
        response = get(f'{SITE_NAME}/{path}')
    except Exception as e:
        print(e)
        return Response()
    content = response.content
    parsed_url = urlparse(response.url)
    if response.headers['Content-Type'].startswith('text/html'):
        bs = BeautifulSoup(content, 'html.parser')
        url = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_url)
        __replace_path(bs, url)
        __add_tm(bs)
        content = bs.encode()
    excluded_headers = [
        'content-encoding', 'content-length',
        'transfer-encoding', 'connection'
    ]
    headers = [
        (name, value) for (name, value) in response.raw.headers.items()
        if name.lower() not in excluded_headers
    ]
    result = Response(content, response.status_code, headers)

    return result


app.run(host='0.0.0.0', port=PORT)
