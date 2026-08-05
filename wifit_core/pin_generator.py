"""Complete WPS PIN generation with all 30 algorithms.

Implements the full set of known vendor-specific and generic PIN algorithms,
plus all documented static PINs. Each generator validates input and returns
an 8-digit PIN with correct WPS checksum.
"""

from __future__ import annotations

import re
from typing import Callable


_MAC_PATTERN = re.compile(r"^(?:[0-9A-Fa-f]{2}([:\-])[0-9A-Fa-f]{2}(?:\1[0-9A-Fa-f]{2}){4}|[0-9A-Fa-f]{12})$")


class MACAddress:
    """Normalized MAC address with integer and string representations."""

    def __init__(self, mac: str | int) -> None:
        if isinstance(mac, int):
            if mac < 0 or mac > 0xFFFFFFFFFFFF:
                raise ValueError(f"MAC integer must be in range 0..281474976710655: {mac}")
            self._integer = mac
            self._string = self._format_mac(mac)
        elif isinstance(mac, str):
            normalized = mac.strip().upper()
            if not _MAC_PATTERN.fullmatch(normalized):
                raise ValueError(f"Invalid MAC address format: {mac!r}")
            cleaned = re.sub(r"[:\-.]", "", normalized)
            self._integer = int(cleaned, 16)
            self._string = ":".join(cleaned[i:i+2] for i in range(0, 12, 2))
        else:
            raise TypeError(f"MAC must be str or int, not {type(mac).__name__}")

    @property
    def integer(self) -> int:
        return self._integer

    @property
    def string(self) -> str:
        return self._string

    @property
    def octets(self) -> tuple[int, int, int, int, int, int]:
        """Return six integer octets."""
        return tuple(int(self._string[i:i+2], 16) for i in range(0, 17, 3))  # type: ignore[return-value]

    @staticmethod
    def _format_mac(value: int) -> str:
        hex_str = f"{value:012X}"
        return ":".join(hex_str[i:i+2] for i in range(0, 12, 2))

    def __str__(self) -> str:
        return self._string

    def __repr__(self) -> str:
        return f"MACAddress({self._string!r})"

    def __int__(self) -> int:
        return self._integer

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MACAddress):
            return self._integer == other._integer
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._integer)


def wps_checksum(pin: int) -> int:
    """Compute the WPS PIN checksum digit.
    
    The WPS specification processes digits from right to left (least significant first):
    accum = 3×d₇ + d₆ + 3×d₅ + d₄ + 3×d₃ + d₂ + 3×d₁
    checksum = (10 - (accum mod 10)) mod 10
    """
    if pin < 0 or pin > 9999999:
        raise ValueError(f"PIN must be 7 digits (0..9999999): {pin}")
    accum = 0
    current = pin
    while current:
        accum += 3 * (current % 10)
        current //= 10
        if current:
            accum += (current % 10)
            current //= 10
    return (10 - (accum % 10)) % 10


def format_pin(pin: int | str) -> str:
    """Format a 7-digit integer or 8-digit string as an 8-digit WPS PIN."""
    if isinstance(pin, str):
        if not pin.isdigit() or len(pin) != 8:
            raise ValueError(f"PIN string must be exactly 8 digits: {pin!r}")
        # Validate checksum
        first_seven = int(pin[:7])
        expected_checksum = wps_checksum(first_seven)
        if int(pin[7]) != expected_checksum:
            raise ValueError(f"PIN {pin!r} has invalid checksum")
        return pin
    
    if pin < 0 or pin > 9999999:
        raise ValueError(f"PIN must be 7 digits (0..9999999): {pin}")
    checksum_digit = wps_checksum(pin)
    return f"{pin:07d}{checksum_digit}"


class PINGenerator:
    """Generate WPS PINs using vendor-specific and generic algorithms."""

    def __init__(self) -> None:
        # Map algorithm IDs to their generation functions
        self._algorithms: dict[str, Callable[[MACAddress], int | str]] = {
            # Generic MAC-based algorithms
            "pin24": self._pin24,
            "pin28": self._pin28,
            "pin32": self._pin32,
            "pin36": self._pin36,
            "pin40": self._pin40,
            "pin44": self._pin44,
            
            # Vendor-specific MAC-based
            "pinDLink": self._pin_dlink,
            "pinDLink1": self._pin_dlink_plus1,
            "pinASUS": self._pin_asus,
            "pinAirocon": self._pin_airocon,
            "pinInvNIC": self._pin_inverted_nic,
            "pinNIC2": self._pin_nic2,
            "pinNIC3": self._pin_nic3,
            "pinOUIaddNIC": self._pin_oui_add_nic,
            "pinOUIsubNIC": self._pin_oui_sub_nic,
            "pinOUIxorNIC": self._pin_oui_xor_nic,
            
            # Static PINs (manufacturer defaults)
            "pinEmpty": lambda mac: "",
            "pinCisco": lambda mac: 1234567,
            "pinBrcm1": lambda mac: 2017252,
            "pinBrcm2": lambda mac: 4626484,
            "pinBrcm3": lambda mac: 7622990,
            "pinBrcm4": lambda mac: 6232714,
            "pinBrcm5": lambda mac: 1086411,
            "pinBrcm6": lambda mac: 3195719,
            "pinAirc1": lambda mac: 3043203,
            "pinAirc2": lambda mac: 7141225,
            "pinDSL2740R": lambda mac: 6817554,
            "pinRealtek1": lambda mac: 9566146,
            "pinRealtek2": lambda mac: 9571911,
            "pinRealtek3": lambda mac: 4856371,
            "pinUpvel": lambda mac: 2085483,
            "pinUR814AC": lambda mac: 4397768,
            "pinUR825AC": lambda mac: 529417,
            "pinOnlime": lambda mac: 9995604,
            "pinEdimax": lambda mac: 3561153,
            "pinThomson": lambda mac: 6795814,
            "pinHG532x": lambda mac: 3425928,
            "pinH108L": lambda mac: 9422988,
            "pinONO": lambda mac: 9575521,
        }
        
        # Vendor prefixes that suggest specific algorithms
        self._vendor_hints: dict[str, list[str]] = {
            "pin24": ["04BF6D", "0E5D4E", "107BEF", "14A9E3", "28285D", "2A285D",
                      "32B2DC", "381766", "404A03", "4E5D4E", "5067F0", "5CF4AB",
                      "6A285D", "8E5D4E", "AA285D", "B0B2DC", "C86C87", "CC5D4E",
                      "CE5D4E", "EA285D", "E243F6", "EC43F6", "EE43F6", "F2B2DC",
                      "FCF528", "FEF528"],
            "pin28": ["200BC7", "4846FB", "D46AA8", "F84ABF"],
            "pin32": ["000726", "D8FEE3", "FC8B97", "1062EB", "1C5F2B", "48EE0C",
                      "802689", "908D78", "E8CC18"],
            "pinDLink": ["14D64D", "1C7EE5", "28107B", "84C9B2", "A0AB1B", "B8A386",
                         "C0A0BB", "CCB255", "FC7516", "0014D1", "D8EB97"],
            "pinDLink1": ["0018E7", "00195B", "001CF0", "001E58", "002191", "0022B0",
                          "002401", "00265A", "14D64D"],
            "pinASUS": ["049226", "04D9F5", "08606E", "0862669", "107B44", "10BF48",
                        "10C37B", "14DDA9", "1C872C", "2C56DC", "305A3A", "382C4A",
                        "38D547", "40167E", "50465D", "54A050", "6045CB", "60A44C",
                        "704D7B", "74D02B", "7824AF", "88D7F6", "9C5C8E", "AC220B",
                        "AC9E17", "B06EBF", "BCEE7B", "C860007", "D017C2", "D850E6",
                        "E03F49", "F0795978", "F832E4"],
            "pinAirocon": ["0007262F", "000B2B4A", "000EF4E7", "001333B", "00177C", "001AEF"],
        }

    def generate(self, algorithm: str, mac: str | MACAddress) -> str:
        """Generate a WPS PIN using the specified algorithm and MAC address.
        
        Args:
            algorithm: Algorithm identifier (e.g., "pin24", "pinASUS", "pinEmpty")
            mac: MAC address as string or MACAddress object
            
        Returns:
            8-digit PIN string with checksum, or empty string for pinEmpty
            
        Raises:
            ValueError: If algorithm is unknown or MAC is invalid
        """
        if algorithm not in self._algorithms:
            raise ValueError(
                f"Unknown algorithm: {algorithm!r}. "
                f"Available: {', '.join(sorted(self._algorithms.keys()))}"
            )
        
        mac_addr = mac if isinstance(mac, MACAddress) else MACAddress(mac)
        result = self._algorithms[algorithm](mac_addr)
        
        if algorithm == "pinEmpty":
            return ""
        
        if isinstance(result, str):
            return result
        
        # Apply checksum to integer results
        pin_7digit = result % 10000000
        return format_pin(pin_7digit)

    def get_suggested(self, mac: str | MACAddress) -> list[tuple[str, str]]:
        """Return (algorithm_id, pin) pairs suggested for this MAC's OUI.
        
        Suggestions are based on known vendor OUI patterns. Generic algorithms
        and all static PINs are always included after vendor-specific ones.
        """
        mac_addr = mac if isinstance(mac, MACAddress) else MACAddress(mac)
        mac_upper = mac_addr.string.replace(":", "").upper()
        
        suggested: list[str] = []
        
        # Check vendor-specific hints
        for algo_id, prefixes in self._vendor_hints.items():
            if any(mac_upper.startswith(prefix.upper()) for prefix in prefixes):
                suggested.append(algo_id)
        
        # Add generic MAC algorithms if not already suggested
        for algo_id in ["pin24", "pin28", "pin32", "pin36", "pin40", "pin44"]:
            if algo_id not in suggested:
                suggested.append(algo_id)
        
        # Add vendor-specific algorithms not yet tried
        for algo_id in ["pinDLink", "pinDLink1", "pinASUS", "pinAirocon",
                        "pinInvNIC", "pinNIC2", "pinNIC3", "pinOUIaddNIC",
                        "pinOUIsubNIC", "pinOUIxorNIC"]:
            if algo_id not in suggested:
                suggested.append(algo_id)
        
        # Add all static PINs last
        static_algos = [aid for aid, func in self._algorithms.items() 
                       if aid.startswith("pin") and aid not in suggested
                       and aid != "pinEmpty"]
        suggested.extend(sorted(static_algos))
        
        return [(algo_id, self.generate(algo_id, mac_addr)) for algo_id in suggested]

    def get_all(self, mac: str | MACAddress, *, include_static: bool = True) -> list[tuple[str, str]]:
        """Return (algorithm_id, pin) for all algorithms."""
        mac_addr = mac if isinstance(mac, MACAddress) else MACAddress(mac)
        results: list[tuple[str, str]] = []
        
        for algo_id in sorted(self._algorithms.keys()):
            if not include_static and algo_id.startswith("pin") and algo_id not in {
                "pin24", "pin28", "pin32", "pin36", "pin40", "pin44",
                "pinDLink", "pinDLink1", "pinASUS", "pinAirocon",
                "pinInvNIC", "pinNIC2", "pinNIC3", "pinOUIaddNIC",
                "pinOUIsubNIC", "pinOUIxorNIC", "pinEmpty"
            }:
                continue
            
            results.append((algo_id, self.generate(algo_id, mac_addr)))
        
        return results

    # Generic MAC-based algorithms
    
    @staticmethod
    def _pin24(mac: MACAddress) -> int:
        """Use lower 24 bits of MAC."""
        return mac.integer & 0xFFFFFF

    @staticmethod
    def _pin28(mac: MACAddress) -> int:
        """Use lower 28 bits of MAC."""
        return mac.integer & 0xFFFFFFF

    @staticmethod
    def _pin32(mac: MACAddress) -> int:
        """Use lower 32 bits of MAC."""
        return mac.integer & 0xFFFFFFFF

    @staticmethod
    def _pin36(mac: MACAddress) -> int:
        """Use lower 36 bits of MAC."""
        return mac.integer & 0xFFFFFFFFF

    @staticmethod
    def _pin40(mac: MACAddress) -> int:
        """Use lower 40 bits of MAC."""
        return mac.integer & 0xFFFFFFFFFF

    @staticmethod
    def _pin44(mac: MACAddress) -> int:
        """Use lower 44 bits of MAC."""
        return mac.integer & 0xFFFFFFFFFFF

    # Vendor-specific algorithms
    
    @staticmethod
    def _pin_dlink(mac: MACAddress) -> int:
        """D-Link PIN algorithm."""
        nic = mac.integer & 0xFFFFFF
        pin = nic ^ 0x55AA55
        pin ^= (((pin & 0xF) << 4) +
                ((pin & 0xF) << 8) +
                ((pin & 0xF) << 12) +
                ((pin & 0xF) << 16) +
                ((pin & 0xF) << 20))
        pin %= 10000000
        if pin < 1000000:
            pin += ((pin % 9) * 1000000) + 1000000
        return pin

    def _pin_dlink_plus1(self, mac: MACAddress) -> int:
        """D-Link PIN algorithm with MAC+1."""
        incremented = MACAddress(mac.integer + 1)
        return self._pin_dlink(incremented)

    @staticmethod
    def _pin_asus(mac: MACAddress) -> int:
        """ASUS PIN algorithm."""
        octets = mac.octets
        pin_str = ""
        for i in range(7):
            pin_str += str((octets[i % 6] + octets[5]) % 
                          (10 - (i + octets[1] + octets[2] + octets[3] + octets[4] + octets[5]) % 7))
        return int(pin_str)

    @staticmethod
    def _pin_airocon(mac: MACAddress) -> int:
        """Airocon Realtek PIN algorithm."""
        b = mac.octets
        pin = ((b[0] + b[1]) % 10)
        pin += (((b[5] + b[0]) % 10) * 10)
        pin += (((b[4] + b[5]) % 10) * 100)
        pin += (((b[3] + b[4]) % 10) * 1000)
        pin += (((b[2] + b[3]) % 10) * 10000)
        pin += (((b[1] + b[2]) % 10) * 100000)
        pin += (((b[0] + b[1]) % 10) * 1000000)
        return pin

    @staticmethod
    def _pin_inverted_nic(mac: MACAddress) -> int:
        """Inverted NIC (ones' complement of lower 24 bits)."""
        nic = mac.integer & 0xFFFFFF
        return (~nic) & 0xFFFFFF

    @staticmethod
    def _pin_nic2(mac: MACAddress) -> int:
        """NIC² mod 10⁷."""
        nic = mac.integer & 0xFFFFFF
        return (nic * nic) % 10000000

    @staticmethod
    def _pin_nic3(mac: MACAddress) -> int:
        """NIC³ mod 10⁷."""
        nic = mac.integer & 0xFFFFFF
        return (nic * nic * nic) % 10000000

    @staticmethod
    def _pin_oui_add_nic(mac: MACAddress) -> int:
        """OUI + NIC."""
        oui = (mac.integer >> 24) & 0xFFFFFF
        nic = mac.integer & 0xFFFFFF
        return (oui + nic) % 10000000

    @staticmethod
    def _pin_oui_sub_nic(mac: MACAddress) -> int:
        """OUI - NIC (absolute value)."""
        oui = (mac.integer >> 24) & 0xFFFFFF
        nic = mac.integer & 0xFFFFFF
        return abs(oui - nic) % 10000000

    @staticmethod
    def _pin_oui_xor_nic(mac: MACAddress) -> int:
        """OUI ⊕ NIC."""
        oui = (mac.integer >> 24) & 0xFFFFFF
        nic = mac.integer & 0xFFFFFF
        return (oui ^ nic) % 10000000


def generate_pin(algorithm: str, mac: str) -> str:
    """Convenience function to generate a single PIN."""
    return PINGenerator().generate(algorithm, mac)


def get_likely_pins(mac: str) -> list[str]:
    """Return likely PINs for this MAC in priority order (no duplicates)."""
    generator = PINGenerator()
    suggested = generator.get_suggested(mac)
    seen: set[str] = set()
    unique: list[str] = []
    for _algo_id, pin in suggested:
        if pin and pin not in seen:
            seen.add(pin)
            unique.append(pin)
    return unique


__all__ = [
    "MACAddress",
    "PINGenerator",
    "format_pin",
    "generate_pin",
    "get_likely_pins",
    "wps_checksum",
]
