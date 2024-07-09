from pydantic import BaseModel, Field, field_validator
from typing import Optional
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
    """
    content: str = Field(..., description='The content of this record')
    disabled: bool = Field(default=False, description='Whether or not this record is disabled')


class RRSet(BaseModel):
    name: str = Field(..., description='Record name')
    rtype: str = Field(..., serialization_alias='type', description='Record type')
    ttl: int = Field(default=3600, description='Record time to live')
    changetype: str = Field(default='REPLACE', description='API keyword DELETE or REPLACE')
    records: list[Record] = Field(..., description='All records in this RRSet')
    comments: Optional[list[Comment]] = Field(default_factory=list, description='List of comments')

    @field_validator('records', mode='before')
    @classmethod
    def validate_records(cls, v):
        if isinstance(v, list):
            records = []
            for item in v:
                if isinstance(item, str):
                    records.append(Record(content=item))
                elif isinstance(item, dict):
                    records.append(Record(**item))
                elif isinstance(item, Record):
                    records.append(item)
            return records
        elif isinstance(v, str):
            return [Record(content=v)]
        raise ValueError(f"Invalid records format: {v}")

    def __repr__(self):
        return f"RRSet(name={repr(self.name)}, type={repr(self.rtype)}, records={repr(self.records)}, ttl={self.ttl}, changetype={repr(self.changetype)}, comments={repr(self.comments)})"

    def __str__(self):
        return f"(ttl={self.ttl}) {self.name}  {self.rtype}  {self.records} {self.comments}"

    def ensure_canonical(self, zone: str):
        """
        Ensure all record names are in canonical form.

        This method appends the zone to the record name if it's not already present.
        For CNAME records, it also ensures the record content is in canonical form.

        Args:
            zone (str): The zone name to be appended. Must end with a dot.

        Raises:
            ValueError: If the provided zone is not in canonical form (doesn't end with a dot).

        Note:
            This method modifies the RRSet in-place. The changes cannot be reverted.
        """
        if not zone.endswith('.'):
            raise ValueError(f"Zone {zone} is not canonical.")
        if not self.name.endswith('.'):
            self.name += f".{zone}"
        if self.rtype == 'CNAME':
            for record in self.records:
                if not record.content.endswith('.'):
                    record.content += f".{zone}"

