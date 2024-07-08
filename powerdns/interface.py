from .exceptions import PDNSCanonicalError
import logging
import json
import os

LOG = logging.getLogger(__name__)

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
            LOG.info("Getting available servers from API")
            self._servers = [PDNSServer(self.api_client, data)
                             for data in self._get('/servers')]
        LOG.info(f"{len(self._servers)} server(s) listed")
        return self._servers

class PDNSServer(PDNSEndpointBase):
    """Powerdns API Server Endpoint"""
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
            LOG.info("Getting server configuration")
            self._config = self._get(f'{self.url}/config')
        return self._config

    @property
    def zones(self):
        """List of DNS zones on a PowerDNS server

        PowerDNS API is queried and results are cached. This cache is
        reset in case of zone creation, deletion, or restoration.
        """
        if not self._zones:
            LOG.info("Getting available zones from API")
            self._zones = [PDNSZone(self.api_client, self, data)
                           for data in self._get(f'{self.url}/zones')]
        LOG.info(f"{len(self._zones)} zone(s) listed")
        return self._zones

    def search(self, search_term, max_result=100):
        """Search term using API search endpoint

        :param str search_term: Term to search for
        :param int max_result: Maximum number of results to return
        :return: Query results as list
        """
        LOG.info(f"API search terms: {search_term}")
        results = self._get(f'{self.url}/search-data?q={search_term}&max={max_result}')
        LOG.info(f"{len(results)} search result(s)")
        return results

    def get_zone(self, name):
        """Get zone by name

        :param str name: Zone name (canonical)
        :return: Zone as PDNSZone instance or None
        """
        LOG.info(f"Getting zone: {name}")
        return next((zone for zone in self.zones if zone.name == name), None)

    def suggest_zone(self, r_name):
        """Suggest best matching zone from existing zone

        :param str r_name: Record canonical name
        :return: Zone as PDNSZone object or None
        """
        LOG.info(f"Suggesting zone for: {r_name}")
        if not r_name.endswith('.'):
            raise PDNSCanonicalError(r_name)
        return max((zone for zone in self.zones if r_name.endswith(zone.name)),
                   key=lambda z: len(z.name), default=None)

    def create_zone(self, name, kind, nameservers, masters=None, servers=None,
                    rrsets=None, update=False):
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
            LOG.info(f"Updating zone: {name}")
            zone = self.get_zone(name)
            zone_data = self._patch(f"{self.url}/zones/{zone.id}", data=zone_data)
        else:
            LOG.info(f"Creating zone: {name}")
            zone_data = self._post(f"{self.url}/zones", data=zone_data)

        if zone_data:
            self._zones = None
            LOG.info(f"Zone {name} successfully processed")
            return PDNSZone(self.api_client, self, zone_data)

    def delete_zone(self, name):
        """Delete a zone

        :param str name: Zone name
        :return: PDNSApiClient response
        """
        self._zones = None
        LOG.info(f"Deleting zone: {name}")
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
        LOG.info(f"Restoring zone: {zone_name}")
        zone_data = self._post(f"{self.url}/zones", data=zone_data)
        if zone_data:
            LOG.info(f"Zone successfully restored: {zone_data['name']}")
            return PDNSZone(self.api_client, self, zone_data)
        LOG.info(f"{zone_name} zone restoration failed")

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
            LOG.info(f"Getting {self.name} zone details from API")
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
        LOG.info(f"Getting zone record: {name}")
        return [record for record in self.details['rrsets'] if name == record['name']]

    def create_records(self, rrsets):
        """Create resource record sets

        :param list rrsets: Resource record sets
        :return: Query response
        """
        LOG.info(f"Creating {len(rrsets)} record(s) in {self.name}")
        for rrset in rrsets:
            rrset.ensure_canonical(self.name)
            rrset['changetype'] = 'REPLACE'
        self._details = None
        return self._patch(self.url, data={'rrsets': rrsets})

    def delete_records(self, rrsets):
        """Delete resource record sets

        :param list rrsets: Resource record sets
        :return: Query response
        """
        LOG.info(f"Deleting {len(rrsets)} records from {self.name}")
        for rrset in rrsets:
            rrset.ensure_canonical(self.name)
            rrset['changetype'] = 'DELETE'
        self._details = None
        return self._patch(self.url, data={'rrsets': rrsets})

    def backup(self, directory, filename=None, pretty_json=False):
        """Backup zone data to json file

        :param str directory: Directory to store json file
        :param str filename: Json file name
        :param bool pretty_json: Enable pretty json display
        """
        LOG.info(f"Backing up zone: {self.name}")
        filename = filename or f"{self.name.rstrip('.')}.json"
        json_file = os.path.join(directory, filename)
        LOG.info(f"Backup file is {json_file}")
        with open(json_file, "w") as backup_fp:
            json.dump(self.details, backup_fp,
                      ensure_ascii=True,
                      indent=2 if pretty_json else None,
                      sort_keys=True if pretty_json else False)
        LOG.info(f"Zone {self.name} successfully saved")

    def notify(self):
        """Trigger notification for zone updates"""
        LOG.info(f"Notifying of zone: {self.name}")
        return self._put(f"{self.url}/notify")


class RRSet(dict):
    """Resource record data for PowerDNS API

    :param str changetype: API keyword DELETE or REPLACE
    :param str name: Record name
    :param str rtype: Record type
    :param list records: List of Str or Tuple(content_str, disabled_bool)
                         or Dict with the keys "content" and optionally
                         "disabled".
    :param int ttl: Record time to live
    :param list comments: list of Comments instances for this RRSet

    .. seealso:: https://doc.powerdns.com/md/httpapi/api_spec/#url-apiv1serversserver95idzoneszone95id
    """
    def __init__(self, name, rtype, records, ttl=3600, changetype='REPLACE',
                 comments=None):
        """Initialization"""
        LOG.debug("new rrset object for %s", name)
        super(RRSet, self).__init__()
        self.raw_records = records
        self['name'] = name
        self['type'] = rtype
        self['changetype'] = changetype
        self['ttl'] = ttl
        self['records'] = []
        for record in records:
            disabled = False
            if isinstance(record, dict):
                if set(record.keys()) > {"content", "disabled"}:
                    raise ValueError(f"Dictionary { records } has more keys than 'content' and 'disabled'")
                if "content" not in record.keys():
                    raise ValueError(f"Dictionary { records } does not have the 'content' key.")
                if "disabled" not in record.keys():
                    record["disabled"] = False

                self['records'].append(record)
                continue

            if isinstance(record, (list, tuple)):
                disabled = record[1]
                record = record[0]
            self['records'].append({'content': record, 'disabled': disabled})
        if comments is None:
            self["comments"] = list()
        else:
            self["comments"] = comments

    def __repr__(self):
        return "RRSet(%s, %s, %s, %s, %s, %s)" % (
            repr(self['name']),
            repr(self['type']),
            repr(self.raw_records),
            repr(self['ttl']),
            repr(self['changetype']),
            repr(self['comments']),
        )

    def __str__(self):
        records = []

        for record in self.raw_records:
            if isinstance(record, (list, tuple)):
                records += [record[0]]
            else:
                records += [record]

        return "(ttl=%d) %s  %s  %s %s)" % (self['ttl'],
                                            self['name'],
                                            self['type'],
                                            records,
                                            self['comments'],)

    def ensure_canonical(self, zone):
        """Ensure every record names are canonical

        :param str zone: Zone name to build canonical names

        In case of CNAME records, records content is also checked.

        .. warning::

            This method update :class:`RRSet` data to ensure the use of
            canonical names. It is actually not possible to revert values.
        """
        LOG.debug("ensuring rrset %s is canonical", self['name'])
        if not zone.endswith('.'):
            raise PDNSCanonicalError(zone)
        if not self['name'].endswith('.'):
            LOG.debug("transforming %s with %s", self['name'], zone)
            self['name'] += ".%s" % zone
        if self['type'] == 'CNAME':
            for record in self['records']:
                if not record['content'].endswith('.'):
                    LOG.debug("transforming %s with %s",
                              record['content'], zone)
                    record['content'] += ".%s" % zone


class Comment(dict):
    """Comment data for PowerDNS API RRSets

    :param str content: the content of the comment
    :param str account: the account
    :param int modified_at: Unix timestamp at which the comment was last
                            modified. Will be set to the current timestamp if
                            None.

    .. seealso:: https://doc.powerdns.com/md/httpapi/api_spec/#zone95collection
    """

    def __init__(self, content, account="", modified_at=None):
        """Initialization"""
        super(Comment, self).__init__(content=content, account=account)

        if modified_at is None:
            self["modified_at"] = int(time.time())
        else:
            self["modified_at"] = modified_at

    def __repr__(self):
        return "Comment(%s, %s, %s)" % (
            repr(self["content"]),
            repr(self["account"]),
            repr(self["modified_at"]),
        )
