#!/usr/bin/env python3
"""Safely power down one CERN Rev5 PACMAN."""

import argparse

import larpix.io

from base.asic_family import control_io_settings
from base import pacman_base
from runenv import runenv as RUN


def main(pacman_config):
    io_group, _, packet_family = control_io_settings(pacman_config)
    if RUN.iog_pacman_version_[io_group] != "v1rev5":
        raise ValueError("The CERN power-down path supports Rev5 PACMANs only")
    io = larpix.io.PACMAN_IO(
        relaxed=True, config_filepath=pacman_config,
        asic_version=packet_family,
    )
    try:
        pacman_base.disable_all_pacman_uart(io, io_group)
        io.set_reg(0x10, 0, io_group=io_group)
        for tile in range(1, 11):
            offset = tile - 1
            io.set_reg(0x24020 + offset, 0, io_group=io_group)
            io.set_reg(0x24010 + offset, 0, io_group=io_group)
        io.set_reg(0x14, 0, io_group=io_group)
        io.set_reg(0x101C, 0, io_group=io_group)
        print(f"IOG {io_group}: all Rev5 tile outputs, DACs, MCLK, and RX disabled")
    finally:
        io.cleanup()
        io.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pacman_config", required=True)
    main(**vars(parser.parse_args()))
