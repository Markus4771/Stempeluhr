import unittest

from app.services.rfid_media import normalize_rfid_uid


class RfidNormalizationTests(unittest.TestCase):
    def test_common_reader_formats_are_equal(self):
        expected = "04A39F8812AA"
        self.assertEqual(normalize_rfid_uid("04:A3:9F:88:12:AA"), expected)
        self.assertEqual(normalize_rfid_uid("04-a3-9f-88-12-aa\r\n"), expected)
        self.assertEqual(normalize_rfid_uid("04 A3 9F 88 12 AA"), expected)

    def test_empty_uid(self):
        self.assertEqual(normalize_rfid_uid(None), "")
        self.assertEqual(normalize_rfid_uid("  \r\n"), "")


if __name__ == "__main__":
    unittest.main()
