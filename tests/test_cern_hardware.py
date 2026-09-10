import unittest

from base.asic_family import normalize_asic_family, packet_family_for_asic
from base.hijinks import (
    DEAD_LOGICAL_CHANNELS,
    logical_to_physical_uart,
    physical_rx_mask,
)


class FakeIO:
    def __init__(self):
        self.registers = {}
        self.clock_calls = []

    def set_reg(self, address, value, io_group):
        self.registers[(io_group, address)] = value

    def get_reg(self, address, io_group):
        return self.registers.get((io_group, address), 0x5A)

    def set_uart_clock_ratio(self, uart, ratio, io_group):
        self.clock_calls.append((io_group, uart, ratio))
        return ratio


class FamilyPolicyTest(unittest.TestCase):
    def test_supported_mapping(self):
        self.assertEqual(normalize_asic_family("2d"), "2d")
        self.assertEqual(normalize_asic_family(3), 3)
        self.assertEqual(packet_family_for_asic("2d"), 2)
        self.assertEqual(packet_family_for_asic(3), 3)

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            packet_family_for_asic(2)

    def test_larpix_semantic_register_translation(self):
        try:
            from larpix import Chip, Key
        except ModuleNotFoundError:
            self.skipTest("larpix-control is not installed")
        expected = {
            "2d": (118, 119),
            3: (114, 115),
        }
        for family, registers in expected.items():
            chip = Chip(Key(1, 1, 1), version=family)
            self.assertEqual(
                list(chip.config.register_map["digital_monitor_enable"])[0],
                registers[0],
            )
            self.assertEqual(
                list(chip.config.register_map["digital_monitor_chan"])[0],
                registers[1],
            )
            self.assertEqual(
                list(chip.config.register_map["enable_hit_veto"])[0], 128
            )


class HijinksMappingTest(unittest.TestCase):
    def test_mapping_boundaries_and_examples(self):
        self.assertEqual(logical_to_physical_uart(1), 1)
        self.assertEqual(logical_to_physical_uart(27), 23)
        self.assertEqual(logical_to_physical_uart(37), 30)
        self.assertEqual(logical_to_physical_uart(39), 32)

    def test_dead_channels(self):
        self.assertEqual(DEAD_LOGICAL_CHANNELS, frozenset(range(12, 41, 4)))
        for channel in DEAD_LOGICAL_CHANNELS:
            with self.assertRaises(ValueError):
                logical_to_physical_uart(channel)

    def test_active_low_masks(self):
        self.assertEqual(physical_rx_mask([]), 0xFFFFFFFF)
        self.assertEqual(physical_rx_mask([23]), 0xFFBFFFFF)
        self.assertEqual(physical_rx_mask([30]), 0xDFFFFFFF)

    def test_hardware_helpers_translate_before_register_access(self):
        # Importing pacman_base requires larpix in production, so this focused
        # integration check is skipped in minimal analysis environments.
        try:
            from base import pacman_base
        except ModuleNotFoundError as error:
            if error.name == "larpix":
                self.skipTest("larpix-control is not installed")
            raise
        io = FakeIO()
        pacman_base.enable_pacman_uart_from_io_channels(io, 2, [37])
        self.assertEqual(io.registers[(2, 0x201C)], 0xDFFFFFFF)
        pacman_base.set_uart_clock_ratio(io, 2, 37, 1)
        self.assertEqual(io.clock_calls, [(2, 30, 1)])
        pacman_base.set_packet_delay(io, 2, 37, 0xFF)
        self.assertEqual(io.registers[(2, 0x20014)], 0xFF5A)


if __name__ == "__main__":
    unittest.main()
