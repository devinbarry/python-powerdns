import unittest
from powerdns.models import Comment, Record, RRSet


class TestComment(unittest.TestCase):
    def test_comment_creation(self):
        comment = Comment(content="Test comment", account="testuser")
        self.assertEqual(comment.content, "Test comment")
        self.assertEqual(comment.account, "testuser")
        self.assertIsInstance(comment.modified_at, int)

    def test_comment_repr(self):
        comment = Comment(content="Test comment", account="testuser", modified_at=1625097600)
        self.assertEqual(repr(comment), "Comment('Test comment', 'testuser', 1625097600)")


class TestRecord(unittest.TestCase):
    def test_record_creation(self):
        record = Record(content="192.0.2.1")
        self.assertEqual(record.content, "192.0.2.1")
        self.assertFalse(record.disabled)

    def test_record_disabled(self):
        record = Record(content="192.0.2.1", disabled=True)
        self.assertTrue(record.disabled)


class TestRRSet(unittest.TestCase):
    def setUp(self):
        self.rrset = RRSet(
            name="example.com",
            rtype="A",
            records=["192.0.2.1", "192.0.2.2"]
        )

    def test_rrset_creation(self):
        self.assertEqual(self.rrset.name, "example.com")
        self.assertEqual(self.rrset.rtype, "A")
        self.assertEqual(len(self.rrset.records), 2)
        self.assertEqual(self.rrset.ttl, 3600)
        self.assertEqual(self.rrset.changetype, "REPLACE")

    def test_rrset_str(self):
        expected = "(ttl=3600) example.com  A  [Record(content='192.0.2.1', disabled=False), Record(content='192.0.2.2', disabled=False)] []"
        self.assertEqual(str(self.rrset), expected)

    def test_validate_records(self):
        rrset = RRSet(
            name="example.com",
            rtype="A",
            records=["192.0.2.1", {"content": "192.0.2.2", "disabled": True}, "192.0.2.3"]
        )
        self.assertEqual(len(rrset.records), 3)
        self.assertIsInstance(rrset.records[0], Record)
        self.assertIsInstance(rrset.records[1], Record)
        self.assertIsInstance(rrset.records[2], Record)
        self.assertFalse(rrset.records[0].disabled)
        self.assertTrue(rrset.records[1].disabled)
        self.assertFalse(rrset.records[2].disabled)

    def test_ensure_canonical(self):
        self.rrset.ensure_canonical("example.org.")
        self.assertEqual(self.rrset.name, "example.com.example.org.")

        cname_rrset = RRSet(
            name="www",
            rtype="CNAME",
            records=["example.com"]
        )
        cname_rrset.ensure_canonical("example.org.")
        self.assertEqual(cname_rrset.name, "www.example.org.")
        self.assertEqual(cname_rrset.records[0].content, "example.com.example.org.")

    def test_ensure_canonical_invalid_zone(self):
        with self.assertRaises(ValueError):
            self.rrset.ensure_canonical("example.org")
