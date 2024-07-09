from unittest import TestCase
from unittest.mock import MagicMock

from powerdns.client import PDNSApiClient
from powerdns.interface import PDNSEndpoint, PDNSServer, PDNSZone
from powerdns.interface import RRSet
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


class TestRRSetRecords(TestCase):

    def test_dict_correct(self):
        rrset = RRSet("test", "TXT", [{"content": "foo"},
                                      {"content": "bar", "disabled": False},
                                      {"content": "baz", "disabled": True}])

        self.assertEqual(rrset["records"][0],
                         {"content": "foo", "disabled": False})
        self.assertEqual(rrset["records"][1],
                         {"content": "bar", "disabled": False})
        self.assertEqual(rrset["records"][2],
                         {"content": "baz", "disabled": True})

    def test_dict_additional_key(self):
        with self.assertRaises(ValueError):
            RRSet("test", "TXT", [{"content": "baz",
                                   "disabled": False,
                                   "foo": "bar"}])

    def test_dict_missing_key(self):
        with self.assertRaises(ValueError):
            RRSet("test", "TXT", [{"content": "baz",
                                   "disabled": False,
                                   "foo": "bar"}])
