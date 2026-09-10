#!/usr/bin/env python3
"""Inspect or deterministically set persistent Rev5/Hijinks UART clocks."""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from larpix.io import PACMAN_IO

from base.asic_family import control_io_settings, uart_clock_ratio_for_asic
from base.hijinks import logical_to_physical_uart, physical_uart_clock_register


def main(config, logical_channels, set_expected=False):
    io_group, asic_family, packet_family = control_io_settings(config)
    expected = uart_clock_ratio_for_asic(asic_family)
    io = PACMAN_IO(
        relaxed=True,
        config_filepath=config,
        asic_version=packet_family,
        timeout=2000,
    )
    try:
        print(
            f"IOG {io_group}: ASIC {asic_family!r}, expected persistent "
            f"UART clock ratio {expected}"
        )
        for logical in logical_channels:
            physical = logical_to_physical_uart(logical)
            register = physical_uart_clock_register(physical)
            before = io.get_reg(register, io_group=io_group)
            if set_expected:
                io.set_uart_clock_ratio(physical, expected, io_group=io_group)
            after = io.get_reg(register, io_group=io_group)
            action = "set" if set_expected else "check"
            print(
                f"{action}: logical {logical} -> physical UART {physical}, "
                f"register 0x{register:05x}: {before} -> {after} "
                f"(expected {expected})"
            )
            if after != expected:
                raise RuntimeError(
                    f"physical UART {physical} ratio is {after}, expected {expected}"
                )
    finally:
        io.cleanup()
        io.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument(
        "--logical-channels", required=True, type=int, nargs="+",
        help="logical Hijinks channels; PACMAN registers use mapped physical UARTs",
    )
    parser.add_argument(
        "--set-expected", action="store_true",
        help="write the family-specific bench value before verifying readback",
    )
    main(**vars(parser.parse_args()))
