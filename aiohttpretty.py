import sys
import json
import asyncio

import aiohttp


class _AioHttPretty:
    def __init__(self):
        self.calls = []
        self.registry = {}
        self.request = None

    def make_call(self, **kwargs):
        return kwargs

    @asyncio.coroutine
    def process_request(self, **kwargs):
        """Process request options as if the request was actually executed."""
        data = kwargs.get('data')
        if isinstance(data, asyncio.StreamReader):
            yield from data.read()

    @asyncio.coroutine
    def fake_request(self, method, uri, **kwargs):
        try:
            options = self.registry[(method, uri)]
        except KeyError:
            raise Exception('No URLs matching {method} {uri}. Not making request. Go fix your test.'.format(**locals()))

        yield from self.process_request(**kwargs)
        self.calls.append(self.make_call(method=method, uri=uri, **kwargs))
        mock_response = aiohttp.client.ClientResponse(method, uri)
        mock_response._content = options.get('body', 'aiohttpretty')
        mock_response.headers = aiohttp.client.CaseInsensitiveMultiDict(options.get('headers', {}))
        mock_response.status = options.get('status', 200)
        return mock_response

    def register_uri(self, method, uri, **options):
        self.registry[(method, uri)] = options

    def register_json_uri(self, method, uri, **options):
        body = json.dumps(options.pop('body', None)).encode('utf-8')
        headers = {'Content-Type': 'application/json'}
        headers.update(options.pop('headers', {}))
        self.register_uri(method, uri, body=body, headers=headers, **options)

    def activate(self):
        aiohttp.request, self.request = self.fake_request, aiohttp.request

    def deactivate(self):
        aiohttp.request, self.request = self.request, None

    def clear(self):
        self.registry = {}

    def compare_call(self, first, second):
        for key, value in first.items():
            if second.get(key) != value:
                return False
        return True

    def has_call(self, **kwargs):
        for call in self.calls:
            if self.compare_call(kwargs, call):
                return True
        return False


sys.modules[__name__] = _AioHttPretty()
