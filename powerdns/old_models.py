import time
import logging
from .exceptions import PDNSCanonicalError


logger = logging.getLogger(__name__)


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
        logger.debug("new rrset object for %s", name)
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
        logger.debug("ensuring rrset %s is canonical", self['name'])
        if not zone.endswith('.'):
            raise PDNSCanonicalError(zone)
        if not self['name'].endswith('.'):
            logger.debug("transforming %s with %s", self['name'], zone)
            self['name'] += ".%s" % zone
        if self['type'] == 'CNAME':
            for record in self['records']:
                if not record['content'].endswith('.'):
                    logger.debug("transforming %s with %s",
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
