from pydantic import BaseModel, Field, validator
from typing import List, Optional
import time

class Comment(BaseModel):
    """
    A comment about an RRSet.

    content (string) – The actual comment
    account (string) – Name of an account that added the comment
    modified_at (integer) – Timestamp of the last change to the comment
    """
    content: str = Field(..., description='The content of the comment')
    account: str = Field(default="", description='The account')
    modified_at: int = Field(default_factory=lambda: int(time.time()),
                             description='Unix timestamp at which the comment was last modified')

    def __repr__(self):
        return f"Comment({repr(self.content)}, {repr(self.account)}, {repr(self.modified_at)})"


class Record(BaseModel):
    """
    The RREntry object represents a single record.

    content (string) – The content of this record
    disabled (boolean) – Whether or not this record is disabled. When unset, the record is not disabled
    """
    content: str
    disabled: bool = False


class RRSet(BaseModel):
    name: str = Field(..., description='Record name')
    rtype: str = Field(..., alias='type', description='Record type')
    ttl: int = Field(default=3600, description='Record time to live')
    changetype: str = Field(default='REPLACE', description='API keyword DELETE or REPLACE')
    records: List[Record] = Field(..., description='All records in this RRSet')
    comments: Optional[List[Comment]] = Field(default_factory=list, description='List of comments')

    @validator('records', pre=True, each_item=True)
    def validate_records(cls, v):
        if isinstance(v, dict):
            if set(v.keys()) > {"content", "disabled"}:
                raise ValueError(f"Dictionary {v} has more keys than 'content' and 'disabled'")
            if "content" not in v.keys():
                raise ValueError(f"Dictionary {v} does not have the 'content' key.")
            if "disabled" not in v.keys():
                v["disabled"] = False
            return Record(**v)
        elif isinstance(v, (list, tuple)):
            return Record(content=v[0], disabled=v[1])
        elif isinstance(v, str):
            return Record(content=v)
        else:
            raise ValueError(f"Invalid record format: {v}")

    def __repr__(self):
        return "RRSet(%s, %s, %s, %s, %s, %s)" % (
            repr(self.name),
            repr(self.rtype),
            repr(self.records),
            repr(self.ttl),
            repr(self.changetype),
            repr(self.comments),
        )

    def __str__(self):
        return "(ttl=%d) %s  %s  %s %s)" % (
            self.ttl,
            self.name,
            self.rtype,
            self.records,
            self.comments,
        )

    def ensure_canonical(self, zone: str):
        """Ensure every record names are canonical

        :param str zone: Zone name to build canonical names

        In case of CNAME records, records content is also checked.

        .. warning::

            This method updates :class:`RRSet` data to ensure the use of
            canonical names. It is actually not possible to revert values.
        """
        if not zone.endswith('.'):
            raise ValueError(f"Zone {zone} is not canonical.")
        if not self.name.endswith('.'):
            self.name += f".{zone}"
        if self.rtype == 'CNAME':
            for record in self.records:
                if not record.content.endswith('.'):
                    record.content += f".{zone}"
