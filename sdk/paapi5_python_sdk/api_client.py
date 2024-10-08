# coding: utf-8

# flake8: noqa

from __future__ import absolute_import
import datetime
import json
import mimetypes
from multiprocessing.pool import ThreadPool
import os
import re
import tempfile
import threading
import six
from six.moves.urllib.parse import quote

from paapi5_python_sdk.configuration import Configuration
import paapi5_python_sdk.models
from paapi5_python_sdk import rest
from paapi5_python_sdk.auth.sign_helper import AWSV4Auth


class ApiClient(object):
    """Generic API client for Swagger client library builds."""

    PRIMITIVE_TYPES = (float, bool, bytes, six.text_type) + six.integer_types
    NATIVE_TYPES_MAPPING = {
        'int': int,
        'long': int if six.PY3 else long,  # noqa: F821
        'float': float,
        'str': str,
        'bool': bool,
        'date': datetime.date,
        'datetime': datetime.datetime,
        'object': object,
    }

    def __init__(self, access_key=None, secret_key=None, host='webservices.amazon.com', region='us-east-1', configuration=None, header_name=None, header_value=None, cookie=None):
        if not access_key or not secret_key:
            raise ValueError("Access Key and Secret Key must be provided.")

        if configuration is None:
            configuration = Configuration()

        self.configuration = configuration
        self.pool = ThreadPool()
        self.rest_client = rest.RESTClientObject(configuration)
        self.default_headers = {}
        self.cookie = cookie

        # Set default User-Agent.
        self.user_agent = 'paapi5-python-sdk/1.0.0'
        self.access_key = access_key
        self.secret_key = secret_key
        self.host = host
        self.region = region

        print(f"[DEBUG] ApiClient initialized with access_key: {self.access_key}, secret_key: {'*' * len(self.secret_key)}, host: {self.host}, region: {self.region}")

    def __del__(self):
        self.pool.close()
        self.pool.join()

    @property
    def user_agent(self):
        """User agent for this API client"""
        return self.default_headers.get('User-Agent', 'paapi5-python-sdk/1.0.0')

    @user_agent.setter
    def user_agent(self, value):
        self.default_headers['User-Agent'] = value

    def set_default_header(self, header_name, header_value):
        self.default_headers[header_name] = header_value

    def select_header_accept(self, accepts):
        """Returns `Accept` based on an array of accepts provided."""
        if not accepts:
            return
        accepts = [x.lower() for x in accepts]
        if 'application/json' in accepts:
            return 'application/json'
        else:
            return ', '.join(accepts)

    def select_header_content_type(self, content_types):
        """Returns `Content-Type` based on an array of content_types provided."""
        if not content_types:
            return 'application/json'
        content_types = [x.lower() for x in content_types]
        if 'application/json' in content_types or '*/*' in content_types:
            return 'application/json'
        else:
            return content_types[0]

    def call_api(
            self, resource_path, method, api_name=None, path_params=None,
            query_params=None, header_params=None, body=None, post_params=None,
            files=None, response_type=None, auth_settings=None, async_req=None,
            _return_http_data_only=None, collection_formats=None,
            _preload_content=True, _request_timeout=None):
        """Generic method to call APIs."""
        if not self.access_key or not self.secret_key:
            raise ValueError("Missing Credentials (Access Key and Secret Key). Please specify credentials.")

        print(f"[DEBUG] Calling API with access_key: {self.access_key}, secret_key: {'*' * len(self.secret_key)}, host: {self.host}")

        config = self.configuration

        # Header parameters
        header_params = header_params or {}
        header_params.update(self.default_headers)
        if self.cookie:
            header_params['Cookie'] = self.cookie
        if header_params:
            header_params = self.sanitize_for_serialization(header_params)
            header_params = dict(self.parameters_to_tuples(header_params, collection_formats))

        # Path parameters
        if path_params:
            path_params = self.sanitize_for_serialization(path_params)
            path_params = self.parameters_to_tuples(path_params, collection_formats)
            for k, v in path_params:
                resource_path = resource_path.replace(
                    '{%s}' % k,
                    quote(str(v), safe=config.safe_chars_for_path_param)
                )

        # Query parameters
        if query_params:
            query_params = self.sanitize_for_serialization(query_params)
            query_params = self.parameters_to_tuples(query_params, collection_formats)

        # Post parameters
        if post_params or files:
            post_params = self.prepare_post_parameters(post_params, files)
            post_params = self.sanitize_for_serialization(post_params)
            post_params = self.parameters_to_tuples(post_params, collection_formats)

        # Auth settings
        self.update_params_for_auth(header_params, query_params, auth_settings, api_name, method, body, resource_path)

        # Body
        if body:
            body = self.sanitize_for_serialization(body)

        # Request URL
        url = "https://" + self.host + resource_path

        # Asynchronous request
        if async_req:
            thread = threading.Thread(target=self.request, args=(method, url),
                                      kwargs={
                                          'query_params': query_params,
                                          'headers': header_params,
                                          'post_params': post_params,
                                          'body': body,
                                          '_preload_content': _preload_content,
                                          '_request_timeout': _request_timeout
                                      })
            thread.start()
            return thread

        # Synchronous request
        response_data = self.request(
            method, url, query_params=query_params, headers=header_params,
            post_params=post_params, body=body,
            _preload_content=_preload_content,
            _request_timeout=_request_timeout)

        self.last_response = response_data

        return_data = response_data
        if _preload_content:
            if response_type:
                return_data = self.deserialize(response_data, response_type)
            else:
                return_data = None

        if _return_http_data_only:
            return return_data
        else:
            return return_data, response_data.status, response_data.getheaders()

    # Autres méthodes de l'API client...
