import os
import unittest
from unittest.mock import patch

from p1_emulator.main import ingress_port_from_environment


class IngressPortTest(unittest.TestCase):
    def test_reads_valid_port(self) -> None:
        with patch.dict(os.environ, {"INGRESS_PORT": "62001"}):
            self.assertEqual(ingress_port_from_environment(), 62001)

    def test_rejects_empty_port_with_clear_error(self) -> None:
        with patch.dict(os.environ, {"INGRESS_PORT": ""}):
            with self.assertRaisesRegex(
                ValueError, "Home Assistant did not provide INGRESS_PORT"
            ):
                ingress_port_from_environment()

    def test_rejects_invalid_port(self) -> None:
        with patch.dict(os.environ, {"INGRESS_PORT": "not-a-port"}):
            with self.assertRaisesRegex(ValueError, "not a valid port"):
                ingress_port_from_environment()

    def test_rejects_out_of_range_port(self) -> None:
        with patch.dict(os.environ, {"INGRESS_PORT": "70000"}):
            with self.assertRaisesRegex(ValueError, "outside the valid range"):
                ingress_port_from_environment()


if __name__ == "__main__":
    unittest.main()
