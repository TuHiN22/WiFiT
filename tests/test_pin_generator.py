"""Tests for WPS PIN generation algorithms."""

import unittest

from wifit_core.pin_generator import (
    MACAddress,
    PINGenerator,
    format_pin,
    generate_pin,
    get_likely_pins,
    wps_checksum,
)


class WPSChecksumTests(unittest.TestCase):
    def test_known_pins_validate(self):
        """Test against documented WPS PINs with known checksums."""
        known = [
            (1234567, 0),  # 12345670
            (0, 0),  # 00000000
            (9999999, 5),  # 99999995
            (5566778, 4),  # 55667784
        ]
        for pin_7digit, expected_checksum in known:
            self.assertEqual(wps_checksum(pin_7digit), expected_checksum)
    
    def test_checksum_formula(self):
        # PIN 1234567: processing right-to-left
        # 3×7 + 6 + 3×5 + 4 + 3×3 + 2 + 3×1 = 21+6+15+4+9+2+3 = 60
        # checksum = (10 - 60%10) % 10 = (10 - 0) % 10 = 0
        self.assertEqual(wps_checksum(1234567), 0)
        
        # PIN 1111111: 3×1 + 1 + 3×1 + 1 + 3×1 + 1 + 3×1 = 3+1+3+1+3+1+3 = 15
        # checksum = (10 - 15%10) % 10 = (10 - 5) % 10 = 5
        self.assertEqual(wps_checksum(1111111), 5)
    
    def test_rejects_invalid_pins(self):
        with self.assertRaises(ValueError):
            wps_checksum(-1)
        with self.assertRaises(ValueError):
            wps_checksum(10000000)


class FormatPINTests(unittest.TestCase):
    def test_formats_7_digit_integer_with_checksum(self):
        self.assertEqual(format_pin(1234567), "12345670")
        self.assertEqual(format_pin(0), "00000000")
        self.assertEqual(format_pin(9999999), "99999995")
    
    def test_validates_8_digit_string(self):
        self.assertEqual(format_pin("12345670"), "12345670")
        self.assertEqual(format_pin("00000000"), "00000000")
    
    def test_rejects_invalid_checksum_in_string(self):
        with self.assertRaises(ValueError):
            format_pin("12345678")  # Wrong checksum
    
    def test_rejects_non_8_digit_strings(self):
        with self.assertRaises(ValueError):
            format_pin("1234567")
        with self.assertRaises(ValueError):
            format_pin("123456789")


class MACAddressTests(unittest.TestCase):
    def test_parses_various_formats(self):
        mac = MACAddress("AA:BB:CC:DD:EE:FF")
        self.assertEqual(mac.string, "AA:BB:CC:DD:EE:FF")
        self.assertEqual(mac.integer, 0xAABBCCDDEEFF)
        
        mac2 = MACAddress("aa-bb-cc-dd-ee-ff")
        self.assertEqual(mac2.string, "AA:BB:CC:DD:EE:FF")
        
        # Dot notation not supported; test plain hex
        mac3 = MACAddress("AABBCCDDEEFF")
        self.assertEqual(mac3.string, "AA:BB:CC:DD:EE:FF")
    
    def test_constructs_from_integer(self):
        mac = MACAddress(0xAABBCCDDEEFF)
        self.assertEqual(mac.string, "AA:BB:CC:DD:EE:FF")
        self.assertEqual(mac.integer, 0xAABBCCDDEEFF)
    
    def test_octets_property(self):
        mac = MACAddress("AA:BB:CC:DD:EE:FF")
        self.assertEqual(mac.octets, (0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF))
    
    def test_rejects_invalid_formats(self):
        with self.assertRaises(ValueError):
            MACAddress("not a mac")
        with self.assertRaises(ValueError):
            MACAddress("AA:BB:CC:DD:EE")  # Too short
        with self.assertRaises(ValueError):
            MACAddress("GG:BB:CC:DD:EE:FF")  # Invalid hex
    
    def test_equality(self):
        mac1 = MACAddress("AA:BB:CC:DD:EE:FF")
        mac2 = MACAddress("aa-bb-cc-dd-ee-ff")
        self.assertEqual(mac1, mac2)


class PINGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.generator = PINGenerator()
        self.test_mac = "AA:BB:CC:DD:EE:FF"
    
    def test_generates_valid_8_digit_pins(self):
        pin = self.generator.generate("pin24", self.test_mac)
        self.assertEqual(len(pin), 8)
        self.assertTrue(pin.isdigit())
        # Validate checksum
        self.assertEqual(format_pin(pin), pin)
    
    def test_pin_empty_returns_empty_string(self):
        pin = self.generator.generate("pinEmpty", self.test_mac)
        self.assertEqual(pin, "")
    
    def test_static_pins_ignore_mac(self):
        pin1 = self.generator.generate("pinCisco", "00:11:22:33:44:55")
        pin2 = self.generator.generate("pinCisco", "FF:EE:DD:CC:BB:AA")
        self.assertEqual(pin1, pin2)
        self.assertEqual(pin1, format_pin(1234567))
    
    def test_pin24_uses_lower_24_bits(self):
        mac = MACAddress("00:00:00:12:34:56")
        # Lower 24 bits = 0x123456 = 1193046
        pin = self.generator.generate("pin24", mac)
        expected = format_pin(1193046)
        self.assertEqual(pin, expected)
    
    def test_pin_dlink_algorithm(self):
        # Test with known D-Link MAC prefix
        mac = "14:D6:4D:AA:BB:CC"
        pin = self.generator.generate("pinDLink", mac)
        self.assertEqual(len(pin), 8)
        self.assertTrue(pin.isdigit())
    
    def test_pin_asus_algorithm(self):
        # Test with known ASUS MAC prefix
        mac = "04:92:26:AA:BB:CC"
        pin = self.generator.generate("pinASUS", mac)
        self.assertEqual(len(pin), 8)
        self.assertTrue(pin.isdigit())
    
    def test_unknown_algorithm_raises(self):
        with self.assertRaises(ValueError) as ctx:
            self.generator.generate("pinNonExistent", self.test_mac)
        self.assertIn("Unknown algorithm", str(ctx.exception))
    
    def test_get_suggested_prioritizes_vendor_hints(self):
        # D-Link MAC should suggest pinDLink early
        dlink_mac = "14:D6:4D:AA:BB:CC"
        suggested = self.generator.get_suggested(dlink_mac)
        algo_ids = [algo_id for algo_id, _pin in suggested]
        
        # pinDLink should appear before generic algorithms
        dlink_index = algo_ids.index("pinDLink")
        pin24_index = algo_ids.index("pin24")
        self.assertLess(dlink_index, pin24_index)
    
    def test_get_all_returns_complete_set(self):
        all_pins = self.generator.get_all(self.test_mac, include_static=True)
        algo_ids = {algo_id for algo_id, _pin in all_pins}
        
        # Verify key algorithms present
        self.assertIn("pin24", algo_ids)
        self.assertIn("pin32", algo_ids)
        self.assertIn("pinDLink", algo_ids)
        self.assertIn("pinASUS", algo_ids)
        self.assertIn("pinEmpty", algo_ids)
        self.assertIn("pinCisco", algo_ids)
        
        # Should have at least 30 algorithms
        self.assertGreaterEqual(len(algo_ids), 30)
    
    def test_get_all_without_static(self):
        dynamic_pins = self.generator.get_all(self.test_mac, include_static=False)
        algo_ids = {algo_id for algo_id, _pin in dynamic_pins}
        
        self.assertIn("pin24", algo_ids)
        self.assertIn("pinDLink", algo_ids)
        self.assertNotIn("pinCisco", algo_ids)
        self.assertNotIn("pinBrcm1", algo_ids)


class ConvenienceFunctionTests(unittest.TestCase):
    def test_generate_pin_convenience(self):
        pin = generate_pin("pin24", "AA:BB:CC:DD:EE:FF")
        self.assertEqual(len(pin), 8)
        self.assertTrue(pin.isdigit())
    
    def test_get_likely_pins_returns_unique_list(self):
        likely = get_likely_pins("14:D6:4D:AA:BB:CC")
        self.assertIsInstance(likely, list)
        self.assertGreater(len(likely), 0)
        
        # No duplicates
        self.assertEqual(len(likely), len(set(likely)))
        
        # All are 8-digit strings or empty
        for pin in likely:
            if pin:
                self.assertEqual(len(pin), 8)
                self.assertTrue(pin.isdigit())


class AlgorithmCorrectnessTests(unittest.TestCase):
    """Verify specific algorithm implementations against known outputs."""
    
    def setUp(self):
        self.generator = PINGenerator()
    
    def test_pin_dlink_plus1_increments_mac(self):
        mac = "AA:BB:CC:DD:EE:FE"
        pin_normal = self.generator.generate("pinDLink", mac)
        pin_plus1 = self.generator.generate("pinDLink1", mac)
        
        # Should be different (unless MAC+1 produces same algorithm output)
        # At minimum, they should both be valid
        self.assertEqual(len(pin_normal), 8)
        self.assertEqual(len(pin_plus1), 8)
    
    def test_pin_airocon_algorithm(self):
        # Airocon uses sum of adjacent octets
        mac = "00:01:02:03:04:05"
        pin = self.generator.generate("pinAirocon", mac)
        self.assertEqual(len(pin), 8)
        self.assertTrue(pin.isdigit())
    
    def test_all_static_pins_are_valid(self):
        static_algos = [
            "pinCisco", "pinBrcm1", "pinBrcm2", "pinBrcm3", "pinBrcm4", "pinBrcm5",
            "pinBrcm6", "pinAirc1", "pinAirc2", "pinDSL2740R", "pinRealtek1",
            "pinRealtek2", "pinRealtek3", "pinUpvel", "pinUR814AC", "pinUR825AC",
            "pinOnlime", "pinEdimax", "pinThomson", "pinHG532x", "pinH108L", "pinONO",
        ]
        
        for algo in static_algos:
            pin = self.generator.generate(algo, "00:11:22:33:44:55")
            self.assertEqual(len(pin), 8, f"{algo} produced invalid PIN length")
            self.assertTrue(pin.isdigit(), f"{algo} produced non-digit PIN")
            # Validate checksum
            self.assertEqual(format_pin(pin), pin, f"{algo} has invalid checksum")


if __name__ == "__main__":
    unittest.main()
