import logging
import json
import os

from .exceptions import PDNSCanonicalError
from .models import RRSet

logger = logging.getLogger(__name__)


class PDNSEndpointBase:
    """Base class for PowerDNS API endpoints"""
    def __init__(self, api_client):
        self.api_client = api_client
        self._get = api_client.get
        self._post = api_client.post
        self._patch = api_client.patch
        self._put = api_client.put
        self._delete = api_client.delete


class PDNSEndpoint(PDNSEndpointBase):
    """PowerDNS API Endpoint"""
    def __init__(self, api_client):
        super().__init__(api_client)
        self._servers = None

    def __repr__(self):
        return f'PDNSEndpoint({repr(self.api_client)})'

    def __str__(self):
        return str(self.api_client)

    @property
    def servers(self):
        """List PowerDNS servers

        PowerDNS API is queried and results are cached. Received
        data is converted to PDNSServer instances.
        """
        if not self._servers:
            logger.info("Getting available servers from API")
            self._servers = [PDNSServer(self.api_client, data)
                             for data in self._get('/servers')]
        logger.info(f"{len(self._servers)} server(s) listed")
        return self._servers


class PDNSServer(PDNSEndpointBase):
    """Powerdns API Server Endpoint

    :param PDNSApiClient api_client: Cachet API client instance
    :param str api_data: PowerDNS API server data

    api_data structure is received from API, here an example structure::

        {
          "type": "Server",
          "id": "localhost",
          "url": "/api/v1/servers/localhost",
          "daemon_type": "recursor",
          "version": "VERSION",
          "config_url": "/api/v1/servers/localhost/config{/config_setting}",
          "zones_url": "/api/v1/servers/localhost/zones{/zone}",
        }
    """
    def __init__(self, api_client, api_data):
        super().__init__(api_client)
        self._api_data = api_data
        self.sid = api_data['id']
        self.version = api_data['version']
        self.daemon_type = api_data['daemon_type']
        self.url = f'/servers/{self.sid}'
        self._zones = None
        self._config = None

    def __repr__(self):
        return f'PDNSServer({repr(self.api_client)}, {repr(self._api_data)})'

    def __str__(self):
        return self.sid

    @property
    def config(self):
        """Server configuration from PowerDNS API"""
        if not self._config:
            logger.info("Getting server configuration")
            self._config = self._get(f'{self.url}/config')
        return self._config

    @property
    def zones(self):
        """List of DNS zones on a PowerDNS server

        PowerDNS API is queried and results are cached. This cache is
        reset in case of zone creation, deletion, or restoration.
        """
        if not self._zones:
            logger.info("Getting available zones from API")
            self._zones = [PDNSZone(self.api_client, self, data)
                           for data in self._get(f'{self.url}/zones')]
        logger.info(f"{len(self._zones)} zone(s) listed")
        return self._zones

    def search(self, search_term, max_result=100):
        """Search term using API search endpoint

        :param str search_term: Term to search for
        :param int max_result: Maximum number of results to return
        :return: Query results as list
        """
        logger.info(f"API search terms: {search_term}")
        results = self._get(f'{self.url}/search-data?q={search_term}&max={max_result}')
        logger.info(f"{len(results)} search result(s)")
        return results

    def get_zone(self, name):
        """Get zone by name

        :param str name: Zone name (canonical)
        :return: Zone as PDNSZone instance or None
        """
        logger.info(f"Getting zone: {name}")
        return next((zone for zone in self.zones if zone.name == name), None)

    def suggest_zone(self, r_name):
        """Suggest best matching zone from existing zone

        :param str r_name: Record canonical name
        :return: Zone as PDNSZone object or None
        """
        logger.info(f"Suggesting zone for: {r_name}")
        if not r_name.endswith('.'):
            raise PDNSCanonicalError(r_name)
        return max((zone for zone in self.zones if r_name.endswith(zone.name)),
                   key=lambda z: len(z.name), default=None)

    def create_zone(self, name, kind, nameservers, masters=None, servers=None, rrsets=None, update=False):
        """Create or update a (new) zone

        :param str name: Name of zone
        :param str kind: Type of zone
        :param list nameservers: Name servers
        :param list masters: Zone masters
        :param list servers: List of forwarded-to servers (recursor only)
        :param list rrsets: Resource records sets
        :param bool update: If the zone needs to be updated or created
        :return: Created/updated zone as PDNSZone instance or None
        """
        zone_data = {
            "name": name,
            "kind": kind,
            "nameservers": nameservers,
            "masters": masters or [],
            "servers": servers or [],
            "rrsets": rrsets or []
        }

        if update:
            logger.info(f"Updating zone: {name}")
            zone = self.get_zone(name)
            zone_data = self._patch(f"{self.url}/zones/{zone.id}", data=zone_data)
        else:
            logger.info(f"Creating zone: {name}")
            zone_data = self._post(f"{self.url}/zones", data=zone_data)

        if zone_data:
            self._zones = None
            logger.info(f"Zone {name} successfully processed")
            return PDNSZone(self.api_client, self, zone_data)

    def delete_zone(self, name):
        """Delete a zone

        :param str name: Zone name
        :return: PDNSApiClient response
        """
        self._zones = None
        logger.info(f"Deleting zone: {name}")
        return self._delete(f"{self.url}/zones/{name}")

    def restore_zone(self, json_file):
        """Restore a zone from a json file produced by PDNSZone.backup

        :param str json_file: Backup file
        :return: Restored zone as PDNSZone instance or None
        """
        with open(json_file) as backup_fp:
            zone_data = json.load(backup_fp)
        self._zones = None
        zone_name = zone_data['name']
        zone_data['nameservers'] = []
        logger.info(f"Restoring zone: {zone_name}")
        zone_data = self._post(f"{self.url}/zones", data=zone_data)
        if zone_data:
            logger.info(f"Zone successfully restored: {zone_data['name']}")
            return PDNSZone(self.api_client, self, zone_data)
        logger.info(f"{zone_name} zone restoration failed")


class PDNSZone(PDNSEndpointBase):
    """Powerdns API Zone Endpoint"""
    def __init__(self, api_client, server, api_data):
        super().__init__(api_client)
        self.server = server
        self.name = api_data['name']
        self.url = f'{self.server.url}/zones/{self.name}'
        self._details = None

    def __repr__(self):
        return f"PDNSZone({repr(self.api_client)}, {repr(self.server)}, {repr(self._details)})"

    def __str__(self):
        return self.name

    @property
    def details(self):
        """Get zone's detailed data"""
        if not self._details:
            logger.info(f"Getting {self.name} zone details from API")
            self._details = self._get(self.url)
        return self._details

    @property
    def records(self):
        """Get zone's records"""
        return self.details['rrsets']

    def get_record(self, name):
        """Get record data

        :param str name: Record name
        :return: Records data as list
        """
        logger.info(f"Getting zone record: {name}")
        return [record for record in self.details['rrsets'] if name == record['name']]

    # TODO This client needs to be rewritten so that we can check that we get a 204 response here
    def create_records(self, rrsets: list[RRSet]):
        """Create resource record sets

        :param list rrsets: Resource record sets
        :return: Query response
        """
        logger.info(f"Creating {len(rrsets)} record(s) in {self.name}")

        serialized_data = []
        for rrset in rrsets:
            rrset.ensure_canonical(self.name)
            assert rrset.changetype == 'REPLACE'
            serialized_data.append(rrset.model_dump(by_alias=True))
        self._details = None
        return self._patch(self.url, data={'rrsets': serialized_data})

    def delete_records(self, rrsets: list[RRSet]):
        """Delete resource record sets

        :param list rrsets: Resource record sets
        :return: Query response
        """
        logger.info(f"Deleting {len(rrsets)} records from {self.name}")

        serialized_data = []
        for rrset in rrsets:
            rrset.ensure_canonical(self.name)
            assert rrset.changetype == 'DELETE'
            serialized_data.append(rrset.model_dump(by_alias=True))
        self._details = None
        return self._patch(self.url, data={'rrsets': serialized_data})

    def backup(self, directory, filename=None, pretty_json=False):
        """Backup zone data to json file

        :param str directory: Directory to store json file
        :param str filename: Json file name
        :param bool pretty_json: Enable pretty json display
        """
        logger.info(f"Backing up zone: {self.name}")
        filename = filename or f"{self.name.rstrip('.')}.json"
        json_file = os.path.join(directory, filename)
        logger.info(f"Backup file is {json_file}")
        with open(json_file, "w") as backup_fp:
            json.dump(self.details, backup_fp,
                      ensure_ascii=True,
                      indent=2 if pretty_json else None,
                      sort_keys=True if pretty_json else False)
        logger.info(f"Zone {self.name} successfully saved")

    def notify(self):
        """Trigger notification for zone updates"""
        logger.info(f"Notifying of zone: {self.name}")
        return self._put(f"{self.url}/notify")
