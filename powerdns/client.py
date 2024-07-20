import json
import logging
import requests
from .exceptions import PDNSError

logger = logging.getLogger(__name__)


class PDNSApiClient:
    """Powerdns API client

    It implements common HTTP methods GET, POST, PUT, PATCH and DELETE

    :param str api_endpoint: Powerdns API endpoint
    :param str api_key: API key
    :param bool verify: Control SSL certificate validation
    :param int timeout: Request timeout in seconds
    """
    def __init__(self, api_endpoint, api_key, verify=True, timeout=None):
        self._api_endpoint = api_endpoint
        self._api_key = api_key
        self._verify = verify
        self._timeout = timeout

        if not verify:
            logger.debug("removing insecure https connection warnings")
            requests.urllib3.disable_warnings(requests.urllib3.exceptions.InsecureRequestWarning)

        self.request_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def __repr__(self):
        return (f"PDNSApiClient({repr(self._api_endpoint)}, {repr(self._api_key)}, verify={repr(self._verify)}, "
                f"timeout={repr(self._timeout)})")

    def __str__(self):
        return self._api_endpoint

    def request(self, path, method, data=None, **kwargs):
        """Handle requests to API

        :param str path: API endpoint's path to request
        :param str method: HTTP method to use
        :param dict data: Data to send (optional)
        :return: Parsed json response as :class:`dict`

        Additional named argument may be passed and are directly transmitted
        to :meth:`request` method of :class:`requests.Session` object.

        :raise PDNSError: If request's response is an error.
        """
        if self._api_key:
            self.request_headers['X-API-Key'] = self._api_key

        logger.debug("request: original path is %s", path)
        if not path.startswith('http://') and not path.startswith('https://'):
            if path.startswith('/'):
                path = path.lstrip('/')
            url = f"{self._api_endpoint}/{path}"
        else:
            url = path

        if data is None:
            data = {}
        data = json.dumps(data)

        logger.info("request: %s %s", method, url)
        logger.debug("headers: %s", self.request_headers)
        logger.debug("data: %s", data)
        response = requests.request(method, url,
                                    data=data,
                                    headers=self.request_headers,
                                    timeout=self._timeout,
                                    verify=self._verify,
                                    **kwargs)

        logger.info("request response code: %d", response.status_code)
        logger.debug("response: %s", response.text)

        if response.status_code in [200, 201]:
            return response.json()
        elif response.status_code == 204:
            return ""
        elif response.status_code == 404:
            error_message = 'Not found'
        else:
            try:
                error_message = self._get_error(response=response.json())
            except Exception:
                error_message = response.text

        logger.error("raising error code %d", response.status_code)
        logger.debug("error response: %s", error_message)
        raise PDNSError(url=response.url,
                        status_code=response.status_code,
                        message=error_message)

    @staticmethod
    def _get_error(response):
        """Get error message from API response

        :param dict response: API response
        :return: Error message as :func:`str`
        """
        if 'error' in response:
            err = response.get('error')
        elif 'errors' in response:
            err = response.get('errors')
        else:
            err = 'No error message found'
        return err

    def get(self, path, data=None, **kwargs):
        """Perform GET request"""
        return self.request(path, method='GET', data=data, **kwargs)

    def post(self, path, data=None, **kwargs):
        """Perform POST request"""
        return self.request(path, method='POST', data=data, **kwargs)

    def put(self, path, data=None, **kwargs):
        """Perform PUT request"""
        return self.request(path, method='PUT', data=data, **kwargs)

    def patch(self, path, data=None, **kwargs):
        """Perform PATCH request"""
        return self.request(path, method='PATCH', data=data, **kwargs)

    def delete(self, path, data=None, **kwargs):
        """Perform DELETE request"""
        return self.request(path, method='DELETE', data=data, **kwargs)
