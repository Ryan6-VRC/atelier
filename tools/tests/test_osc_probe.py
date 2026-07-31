# tools/tests/test_osc_probe.py
import importlib.util
import struct
import sys
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "osc_probe", Path(__file__).resolve().parent.parent / "osc-probe.py")
p = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p)


class Codec(unittest.TestCase):
    """A codec bug here reads as "the emulator sent nothing", which is why the
    round trip is pinned rather than left to the next live run to notice."""

    def assertRoundTrip(self, address, value, tag):
        (addr, tags, args), = p.decode(p.encode(address, value), [])
        self.assertEqual(addr, address)
        self.assertEqual(tags, "," + tag)
        self.assertEqual(args, [value])

    def test_round_trip_preserves_type(self):
        self.assertRoundTrip("/avatar/parameters/F", 0.5, "f")
        self.assertRoundTrip("/avatar/parameters/I", 7, "i")
        self.assertRoundTrip("/avatar/parameters/T", True, "T")
        self.assertRoundTrip("/avatar/parameters/N", False, "F")
        self.assertRoundTrip("/avatar/change", "avtr_x", "s")

    def test_bool_is_a_tag_carrying_no_payload(self):
        # The wire distinction the emulator and client both depend on: a bool is
        # T/F in the tag string, never an int payload.
        self.assertEqual(p.encode("/b", True), p._pad(b"/b\0") + p._pad(b",T\0"))

    def test_every_address_length_stays_4_byte_aligned(self):
        for name in ("/a", "/ab", "/abc", "/abcd", "/abcde"):
            self.assertEqual(len(p.encode(name, 1)) % 4, 0, name)

    def test_bundle_yields_each_element(self):
        inner = [p.encode("/one", 1), p.encode("/two", 2.0)]
        packet = b"#bundle\0" + b"\0" * 8
        for element in inner:
            packet += struct.pack(">i", len(element)) + element
        self.assertEqual([m[0] for m in p.decode(packet, [])], ["/one", "/two"])


class MalformedInput(unittest.TestCase):
    """Refusing beats guessing: argument sizes are tag-derived, so one unknown tag
    desynchronises the cursor and every later value decodes from a wrong offset."""

    def test_unknown_tag_refuses_rather_than_corrupting_the_rest(self):
        packet = (p._pad(b"/t\0") + p._pad(b",df\0")
                  + struct.pack(">d", 1.5) + struct.pack(">f", 9.25))
        with self.assertRaises(p.Malformed):
            p.decode(packet, [])

    def test_truncated_argument_refuses(self):
        with self.assertRaises(p.Malformed):
            p.decode(p._pad(b"/t\0") + p._pad(b",f\0") + b"\x01\x02", [])

    def test_unterminated_string_refuses(self):
        with self.assertRaises(p.Malformed):
            p.decode(b"/no-null-here", [])


class SendSpecs(unittest.TestCase):
    def test_types_are_exact_because_the_far_end_does_not_coerce(self):
        self.assertIsInstance(p.parse_send("/a=1")[1], int)
        self.assertIsInstance(p.parse_send("/a=1.0")[1], float)
        self.assertIsInstance(p.parse_send("/a=1e3")[1], float)
        self.assertIs(p.parse_send("/a=true")[1], True)
        self.assertIs(p.parse_send("/a=False")[1], False)

    def test_shell_mangled_address_exits_naming_the_fix(self):
        with self.assertRaises(SystemExit) as caught:
            p.parse_send("C:/Program Files/Git/avatar/parameters/X=1")
        self.assertIn("MSYS_NO_PATHCONV=1", str(caught.exception))

    def test_missing_assignment_exits(self):
        with self.assertRaises(SystemExit):
            p.parse_send("/avatar/parameters/X")


if __name__ == "__main__":
    unittest.main()
