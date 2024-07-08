from unittest import TestCase
from unittest.mock import patch, Mock
from powerdns.exceptions import PDNSError

from . import API_CLIENT, PDNS_API, PDNS_KEY


class TestClient(TestCase):

    def test_client_repr_and_str(self):
        repr_str = "PDNSApiClient('%s', '%s', verify=False, timeout=None)" % (
            PDNS_API, PDNS_KEY
        )
        self.assertEqual(repr(API_CLIENT), repr_str)
        self.assertEqual(str(API_CLIENT), PDNS_API)

    @patch('powerdns.client.requests.request')
    def test_client_full_uri(self, mock_request):
        # Mock the response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{'id': 'localhost'}]
        mock_request.return_value = mock_response

        result = API_CLIENT.get(PDNS_API + "/servers")

        self.assertIsInstance(result, list)
        self.assertEqual(result, [{'id': 'localhost'}])
        mock_request.assert_called_once_with(
            'GET',
            PDNS_API + "/servers",
            data='{}',
            headers=API_CLIENT.request_headers,
            timeout=None,
            verify=False
        )

    @patch('powerdns.client.requests.request')
    def test_client_error_handling(self, mock_request):
        # Mock an error response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {'error': 'Not Found'}
        mock_request.return_value = mock_response

        with self.assertRaises(PDNSError) as context:
            API_CLIENT.get(PDNS_API + "/nonexistent")

        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.message, 'Not Found')
