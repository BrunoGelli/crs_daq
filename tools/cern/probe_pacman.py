#!/usr/bin/env python3

import argparse

from larpix.io import PACMAN_IO


READ_ONLY_REGISTERS = {
    "tile_enable_mask": 0x00000010,
    "global_power_enable": 0x00000014,
    "clock_control": 0x00001010,
    "reset_cycles": 0x00001014,
    "mclk_control": 0x0000101C,
    "rev5_rx_enable": 0x0000201C,
}


def main():
    parser = argparse.ArgumentParser(
        description="Read-only PACMAN connectivity/register probe"
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--io-group", required=True, type=int)
    parser.add_argument("--asic-version", required=True, type=int, choices=[2, 3])
    args = parser.parse_args()

    print("PACMAN read-only probe")
    print(f"  config:       {args.config}")
    print(f"  io_group:     {args.io_group}")
    print(f"  ASIC packet:  v{args.asic_version}")
    print()

    io = PACMAN_IO(
        relaxed=True,
        config_filepath=args.config,
        asic_version=args.asic_version,
        timeout=2000,
    )

    try:
        print("PING")
        pong = io.ping(io_group=args.io_group)
        print(f"  response: {pong}")
        print()

        if not pong:
            raise RuntimeError("PACMAN did not respond to ping")

        print("REGISTER READBACK")
        for name, address in READ_ONLY_REGISTERS.items():
            try:
                value = io.get_reg(address, io_group=args.io_group)
                print(
                    f"  {name:20s} "
                    f"0x{address:08x} -> "
                    f"0x{value:08x} ({value})"
                )
            except Exception as exc:
                print(
                    f"  {name:20s} "
                    f"0x{address:08x} -> ERROR: {exc}"
                )

    finally:
        io.cleanup()
        io.join()

    print()
    print("PASS: no registers were written")


if __name__ == "__main__":
    main()
