from unittest import TestCase
from unittest.mock import patch, Mock
from powerdns.exceptions import PDNSError

from powerdns.client import PDNSApiClient


class TestClient(TestCase):

    def setUp(self):
        self.api_endpoint = "https://example.com/api/v1"
        self.api_key = "test_key"
        self.client = PDNSApiClient(self.api_endpoint, self.api_key, verify=False)

    def test_client_repr_and_str(self):
        repr_str = f"PDNSApiClient('{self.api_endpoint}', '{self.api_key}', verify=False, timeout=None)"
        self.assertEqual(repr(self.client), repr_str)
        self.assertEqual(str(self.client), self.api_endpoint)

    @patch('powerdns.client.requests.request')
    def test_client_full_uri(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{'id': 'localhost'}]
        mock_request.return_value = mock_response

        result = self.client.get(self.api_endpoint + "/servers")

        self.assertIsInstance(result, list)
        self.assertEqual(result, [{'id': 'localhost'}])
        mock_request.assert_called_once_with(
            'GET',
            self.api_endpoint + "/servers",
            data='{}',
            headers=self.client.request_headers,
            timeout=None,
            verify=False
        )

    @patch('powerdns.client.requests.request')
    def test_client_error_handling(self, mock_request):
        # Mock an error response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {'error': 'Not found'}
        mock_response.text = 'Not found'
        mock_response.url = self.api_endpoint + "/nonexistent"
        mock_request.return_value = mock_response

        with self.assertRaises(PDNSError) as context:
            self.client.get(self.api_endpoint + "/nonexistent")

        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.message, 'Not found')
