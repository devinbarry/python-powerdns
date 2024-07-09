from unittest import TestCase
from unittest.mock import MagicMock, patch

from powerdns.client import PDNSApiClient
from powerdns.models import RRSet, Record
from powerdns.interface import PDNSEndpoint, PDNSServer, PDNSZone
from powerdns.exceptions import PDNSCanonicalError


class TestEndpoint(TestCase):

    def setUp(self):
        self.mock_client = MagicMock(spec=PDNSApiClient)
        self.api = PDNSEndpoint(self.mock_client)

    def test_endpoint_attributes(self):
        self.assertIsInstance(self.api.api_client, PDNSApiClient)
        self.assertTrue(hasattr(self.api, "servers"))

    def test_endpoint_repr_and_str(self):
        api_client_repr = repr(self.api.api_client)
        api_repr = f"PDNSEndpoint({api_client_repr})"
        self.assertEqual(repr(self.api), api_repr)
        self.assertEqual(str(self.api), str(self.api.api_client))

    def test_endpoint_servers_list(self):
        mock_server_data = {'id': 'localhost', 'url': '/api/v1/servers/localhost', "daemon_type": "recursor",
                            "version": "VERSION",}
        self.mock_client.get.return_value = [mock_server_data]

        servers = self.api.servers

        self.assertIsInstance(servers, list)
        self.assertIsInstance(servers[0], PDNSServer)
        self.mock_client.get.assert_called_once_with('/servers')


class TestServers(TestCase):

    def setUp(self):
        self.mock_client = MagicMock(spec=PDNSApiClient)
        self.mock_server_data = {
            'id': 'localhost',
            'url': '/api/v1/servers/localhost',
            'daemon_type': 'authoritative',
            'version': '4.1.0'
        }
        self.server = PDNSServer(self.mock_client, self.mock_server_data)

    def test_server_object(self):
        self.assertEqual(str(self.server), "localhost")
        self.assertEqual(self.server.sid, "localhost")
        self.assertEqual(self.server.version, "4.1.0")

    def test_server_config(self):
        mock_config = [{'name': 'config1', 'value': 'value1'}]
        self.mock_client.get.return_value = mock_config

        config = self.server.config

        self.assertIsInstance(config, list)
        self.assertIsInstance(config[0], dict)
        self.mock_client.get.assert_called_once_with('/servers/localhost/config')

    def test_server_zones(self):
        mock_zone_data = {'name': 'example.com.', 'kind': 'Native'}
        self.mock_client.get.return_value = [mock_zone_data]

        zones = self.server.zones

        self.assertIsInstance(zones, list)
        self.assertIsInstance(zones[0], PDNSZone)
        self.mock_client.get.assert_called_once_with('/servers/localhost/zones')

    def test_server_create_zone(self):
        zone_name = "test.example.com."
        mock_zone_data = {'name': zone_name, 'kind': 'Native'}
        self.mock_client.post.return_value = mock_zone_data

        zone = self.server.create_zone(name=zone_name, kind="Native", nameservers=[])

        self.assertIsInstance(zone, PDNSZone)
        self.mock_client.post.assert_called_once()

    def test_server_get_zone(self):
        self.server._zones = [
            PDNSZone(self.mock_client, self.server, {'name': 'example.com.'})
        ]

        self.assertIs(self.server.get_zone("nonexistent"), None)
        self.assertIsInstance(self.server.get_zone("example.com."), PDNSZone)

    def test_server_suggest_zone(self):
        self.server._zones = [
            PDNSZone(self.mock_client, self.server, {'name': 'example.com.'})
        ]

        zone = self.server.suggest_zone("sub.example.com.")
        self.assertIsInstance(zone, PDNSZone)
        self.assertEqual(zone.name, "example.com.")

        with self.assertRaises(PDNSCanonicalError):
            self.server.suggest_zone("invalid")


class TestPDNSZone(TestCase):

    def setUp(self):
        self.mock_client = MagicMock(spec=PDNSApiClient)
        self.mock_server = MagicMock(spec=PDNSServer)
        self.mock_server.url = '/servers/localhost'
        self.zone_data = {
            'name': 'example.com.',
            'kind': 'Native',
            'rrsets': [
                {
                    'name': 'www.example.com.',
                    'type': 'A',
                    'ttl': 3600,
                    'records': [{'content': '192.0.2.1', 'disabled': False}]
                }
            ]
        }
        self.zone = PDNSZone(self.mock_client, self.mock_server, self.zone_data)

    def test_zone_initialization(self):
        self.assertEqual(self.zone.name, 'example.com.')
        self.assertEqual(self.zone.url, '/servers/localhost/zones/example.com.')

    def test_zone_str_and_repr(self):
        self.assertEqual(str(self.zone), 'example.com.')
        self.assertIn('PDNSZone', repr(self.zone))
        self.assertIn('example.com.', str(self.zone))  # Changed from repr to str

    def test_zone_details(self):
        self.mock_client.get.return_value = self.zone_data
        details = self.zone.details
        self.assertEqual(details, self.zone_data)
        self.mock_client.get.assert_called_once_with(self.zone.url)

    def test_zone_records(self):
        self.mock_client.get.return_value = self.zone_data
        records = self.zone.records
        self.assertEqual(records, self.zone_data['rrsets'])

    def test_get_record(self):
        self.mock_client.get.return_value = self.zone_data
        record = self.zone.get_record('www.example.com.')
        self.assertEqual(len(record), 1)
        self.assertEqual(record[0]['name'], 'www.example.com.')
        self.assertEqual(record[0]['type'], 'A')

    def test_create_records(self):
        rrsets = [
            RRSet(
                name='new.example.com.',
                rtype='A',
                ttl=300,
                records=[Record(content='192.0.2.2')]
            )
        ]
        self.zone.create_records(rrsets)
        self.mock_client.patch.assert_called_once()
        call_args = self.mock_client.patch.call_args
        self.assertEqual(call_args[0][0], self.zone.url)
        self.assertIn('rrsets', call_args[1]['data'])

    def test_delete_records(self):
        rrsets = [
            RRSet(
                name='www.example.com.',
                rtype='A',
                ttl=3600,
                changetype='DELETE',
                records=[]
            )
        ]
        self.zone.delete_records(rrsets)
        self.mock_client.patch.assert_called_once()
        call_args = self.mock_client.patch.call_args
        self.assertEqual(call_args[0][0], self.zone.url)
        self.assertIn('rrsets', call_args[1]['data'])

    @patch('powerdns.interface.os.path.join')
    @patch('powerdns.interface.open')
    @patch('powerdns.interface.json.dump')
    def test_backup(self, mock_json_dump, mock_open, mock_path_join):
        mock_path_join.return_value = '/path/to/backup/example.com.json'
        self.zone.backup('/path/to/backup')
        mock_open.assert_called_once_with('/path/to/backup/example.com.json', 'w')
        mock_json_dump.assert_called_once()

    def test_notify(self):
        self.zone.notify()
        self.mock_client.put.assert_called_once_with(f"{self.zone.url}/notify")
