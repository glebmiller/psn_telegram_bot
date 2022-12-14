import json

import requests


# Class RequestBuilder
# Builds the http requests from arguments that are passed to it
# Saves the clutter as less repeated code is needed
# For internal use only do not call directly
class RequestBuilder:
    def __init__(self, authenticator):
        self.authenticator = authenticator
        self.country = 'US'
        self.language = 'en'
        self.default_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, '
                                              'like Gecko) Chrome/90.0.4430.212 Safari/537.36',
                                'Accept-Language': 'en-US'}

    def get(self, **kwargs):
        access_token = self.authenticator.obtain_fresh_access_token()
        headers = {
            **self.default_headers,
            'Authorization': 'Bearer {}'.format(access_token)
        }
        if 'headers' in kwargs.keys():
            headers = {**headers, **kwargs['headers']}

        params = None
        if 'params' in kwargs.keys():
            params = kwargs['params']

        data = None
        if 'data' in kwargs.keys():
            data = kwargs['data']

        response = requests.get(
            url=kwargs['url'], headers=headers, params=params, data=data)

        response.raise_for_status()
        return response.json()

    def post(self, **kwargs):
        access_token = self.authenticator.obtain_fresh_access_token()
        headers = {
            **self.default_headers,
            'Authorization': 'Bearer {}'.format(access_token)
        }
        if 'headers' in kwargs.keys():
            headers = {**headers, **kwargs['headers']}

        data = None
        if 'data' in kwargs.keys():
            data = kwargs['data']

        response = requests.post(url=kwargs['url'], headers=headers, data=data)
        response.raise_for_status()
        return response.json()

    def multipart_post(self, **kwargs):
        access_token = self.authenticator.obtain_fresh_access_token()
        headers = {
            **self.default_headers,
            'Authorization': 'Bearer {}'.format(access_token)
        }
        if 'headers' in kwargs.keys():
            headers = {**headers, **kwargs['headers']}

        name = None
        if 'name' in kwargs.keys():
            name = kwargs['name']

        data = None
        if 'data' in kwargs.keys():
            data = kwargs['data']

        response = requests.post(url=kwargs['url'], headers=headers, files={name: (None, json.dumps(data),
                                                                                   'application/json; charset=utf-8')})
        response.raise_for_status()
        return response.json()

    def delete(self, **kwargs):
        access_token = self.authenticator.obtain_fresh_access_token()
        headers = {
            **self.default_headers,
            'Authorization': 'Bearer {}'.format(access_token)
        }
        if 'headers' in kwargs.keys():
            headers = {**headers, **kwargs['headers']}

        params = None
        if 'params' in kwargs.keys():
            params = kwargs['params']

        data = None
        if 'data' in kwargs.keys():
            data = kwargs['data']

        response = requests.delete(
            url=kwargs['url'], headers=headers, params=params, data=data)
        response.raise_for_status()

        # delete operation might not include a body
        # causing response.json() to raise an error
        if response.request.body:
            return response.json()
        else:
            return response.status_code
