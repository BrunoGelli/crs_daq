#!/usr/bin/env python3
"""Configure and power CERN Rev5 PACMAN tiles from RUN_CONFIG.json."""

import argparse
import time

import larpix
import larpix.io

from base.asic_family import control_io_settings
from base import pacman_base
from runenv import runenv as RUN

RESET_CYCLES = 4096


def main(verbose=False, pacman_config="io/pacman.json"):
    io_group, asic_family, packet_family = control_io_settings(pacman_config)
    tiles = RUN.io_group_pacman_tile_[io_group]
    vdda = RUN.iog_VDDA_DAC[io_group]
    vddd = RUN.iog_VDDD_DAC[io_group]
    if RUN.iog_pacman_version_[io_group] != "v1rev5":
        raise ValueError("The CERN hardware path supports Rev5 PACMANs only")

    controller = larpix.Controller()
    controller.io = larpix.io.PACMAN_IO(
        relaxed=True, config_filepath=pacman_config,
        asic_version=packet_family,
    )
    io = controller.io
    if verbose:
        print(f"IOG {io_group}: ASIC {asic_family!r}, packet family {packet_family}, tiles {tiles}")

    pacman_base.disable_all_pacman_uart(io, io_group)
    io.set_reg(0x10, 0, io_group=io_group)
    io.set_reg(0x14, 0, io_group=io_group)
    io.set_reg(0x101C, 4, io_group=io_group)
    io.set_reg(0x14, 1, io_group=io_group)

    tile_mask = 0
    for tile in tiles:
        offset = tile - 1
        io.set_reg(0x24020 + offset, 0, io_group=io_group)
        io.set_reg(0x24010 + offset, 0, io_group=io_group)
        time.sleep(0.1)
        io.set_reg(0x24020 + offset, vddd[offset], io_group=io_group)
        io.set_reg(0x24010 + offset, vdda[offset], io_group=io_group)
        tile_mask |= 1 << offset

    io.set_reg(0x10, tile_mask, io_group=io_group)
    io.reset_larpix(length=RESET_CYCLES, io_group=io_group)
    io.set_reg(0x2014, 0xFFFFFFFF, io_group=io_group)

    for tile in tiles:
        offset = tile - 1
        values = (
            io.get_reg(0x24030 + offset, io_group=io_group),
            io.get_reg(0x24050 + offset, io_group=io_group) / 4,
            io.get_reg(0x24040 + offset, io_group=io_group),
            io.get_reg(0x24060 + offset, io_group=io_group) / 4,
        )
        print(f"tile {tile}: VDDA={values[0]}mV IDDA={values[1]:.2f}mA "
              f"VDDD={values[2]}mV IDDD={values[3]:.2f}mA")

    return controller


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pacman_config", required=True,
                        help="One-PACMAN JSON; aggregate configs are raw-only")
    parser.add_argument("--verbose", "-v", action="store_true")
    main(**vars(parser.parse_args()))
