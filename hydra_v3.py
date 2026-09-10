#!/usr/bin/env python3

import argparse
import time
import json

from base import pacman_base
from base.asic_family import control_io_settings

from larpix import Controller, Key
from larpix.io import PACMAN_IO
from larpix.packet.packet_v3 import Packet_v3



def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--config", required=True)
    parser.add_argument("--io-group", type=int, required=True)
    parser.add_argument("--io-channel", type=int, required=True)
    parser.add_argument("--tile", type=int, default=10)
    parser.add_argument("--file-prefix")

    args = parser.parse_args()

    iog = args.io_group
    logical = args.io_channel

    configured_iog, family, packet_family = control_io_settings(args.config)
    if configured_iog != iog or family != 3:
        raise ValueError(f"{args.config} does not select IOG {iog} / ASIC v3")
    physical = pacman_base.logical_to_physical_uart(logical)

    print("========================================")
    print("V3 HIJINKS ROOT BOOTSTRAP")
    print("========================================")
    print(f"io_group:          {iog}")
    print(f"logical channel:   {logical}")
    print(f"physical UART:     {physical}")
    print()

    io = PACMAN_IO(
        relaxed=True,
        config_filepath=args.config,
        asic_version=packet_family,
        timeout=2000,
    )

    c = Controller()
    c.io = io

    try:

        #
        # Start quiet.
        #
        pacman_base.disable_all_pacman_uart(io, iog)

        print("RX mask initially: "
              f"0x{io.get_reg(pacman_base.RX_MASK_REGISTER, io_group=iog):08x}")

        #
        # v3 donor explicitly sets mapped PHYSICAL UART
        # clock ratio to 1.
        #
        print()
        print("=== PHYSICAL UART SETUP ===")

        ratio = pacman_base.set_uart_clock_ratio(io, iog, logical, 1)

        print(
            f"UART {physical} clock ratio -> "
            f"0x{ratio:08x}"
        )

        #
        # Packet delay is also indexed by PHYSICAL UART.
        #
        delay_reg = pacman_base.PACKET_DELAY_BASE + (physical - 1) * pacman_base.PACKET_DELAY_STRIDE
        old_delay = io.get_reg(delay_reg, io_group=iog)
        new_delay = pacman_base.set_packet_delay(io, iog, logical, 0xff)

        print(
            f"UART {physical} delay "
            f"0x{delay_reg:05x}: "
            f"0x{old_delay:08x} "
            f"-> 0x{new_delay:08x}"
        )

        #
        # Fresh known ASIC state.
        #
        print()
        print("=== HARD RESET ===")

        io.reset_larpix(
            length=4096,
            io_group=iog,
        )

        time.sleep(0.1)

        #
        # The chip is still addressed on the LOGICAL channel.
        #
        key = Key(iog, logical, 1)

        c.add_chip(
            key,
            version=3,
            root=True,
        )

        cfg = c[key].config

        print(f"chip key: {key}")

        #
        # Bootstrap exactly the relevant root communication
        # settings from network_base_FSD_v3.
        #
        print()
        print("=== BOOTSTRAPPING ROOT COMMUNICATION ===")

        registers = []

        for uart in range(4):

            setattr(cfg, f"i_rx{uart}", 3)
            registers.append(f"i_rx{uart}")

            setattr(cfg, f"r_term{uart}", 7)
            registers.append(f"r_term{uart}")

            setattr(cfg, f"v_cm_lvds_tx{uart}", 5)
            registers.append(f"v_cm_lvds_tx{uart}")

        #
        # Donor writes these register groups twice.
        #
        for name in registers:
            c.write_configuration(key, name)

        for name in registers:
            c.write_configuration(key, name)

        cfg.enable_posi = [0, 0, 0, 1]

        c.write_configuration(
            key,
            "enable_posi",
        )
        c.write_configuration(
            key,
            "enable_posi",
        )

        cfg.i_tx_diff2 = 7

        c.write_configuration(
            key,
            "i_tx_diff2",
        )
        c.write_configuration(
            key,
            "i_tx_diff2",
        )

        cfg.tx_slices2 = 15

        c.write_configuration(
            key,
            "tx_slices2",
        )
        c.write_configuration(
            key,
            "tx_slices2",
        )

        #
        # THIS is the critical return path.
        #
        cfg.enable_piso_downstream = [0, 0, 1, 0]

        c.write_configuration(
            key,
            "enable_piso_downstream",
        )

        cfg.enable_piso_upstream = [0, 0, 0, 0]

        c.write_configuration(
            key,
            "enable_piso_upstream",
        )

        time.sleep(0.05)

        #
        # Now enable ONLY the mapped PHYSICAL receiver.
        #
        print()
        print("=== ENABLING RECEIVER ===")

        rx_mask = pacman_base.enable_pacman_uart_from_io_channels(
            io, iog, [logical]
        )

        readback_mask = io.get_reg(
            pacman_base.RX_MASK_REGISTER, io_group=iog,
        )

        print(
            f"logical {logical} "
            f"-> physical {physical}"
        )

        print(
            f"RX mask: "
            f"0x{readback_mask:08x}"
        )

        time.sleep(0.05)

        #
        # Finally attempt a very specific readback.
        #
        print()
        print("=== CHIP-ID READBACK ===")

        chip_id_reg = list(
            cfg.register_map["chip_id"]
        )[0]

        c.reads = []

        c.read_configuration(
            key,
            chip_id_reg,
            timeout=0.5,
            connection_delay=0.01,
        )

        collection = c.reads[-1]

        packets = [
            p for p in collection
            if isinstance(p, Packet_v3)
        ]

        valid = [
            p for p in packets
            if p.has_valid_parity()
        ]

        matches = [
            p for p in valid
            if (
                p.packet_type
                == Packet_v3.CONFIG_READ_PACKET
                and p.io_group == iog
                and p.io_channel == logical
                and p.chip_id == 1
                and p.register_address
                == chip_id_reg
            )
        ]

        print(
            f"received Packet_v3: "
            f"{len(packets)}"
        )

        print(
            f"valid parity:       "
            f"{len(valid)}"
        )

        print(
            f"exact matches:      "
            f"{len(matches)}"
        )

        for p in matches:
            print()
            print("MATCH:")
            print(" ", p)

        if matches:
            print()
            print(
                "PASS: ROOT CHIP COMMUNICATION WORKS"
            )
            prefix = args.file_prefix or f"iog_{iog}-tile_{args.tile}-hydra-network"
            payload = {
                "_config_type": "controller", "name": prefix,
                "asic_version": 3, "layout": "10x16",
                "network": {str(iog): {str(logical): {"nodes": [
                    {"chip_id": 1, "root": True,
                     "miso_us": [None, None, None, "ext"]}
                ]}}, "miso_us_uart_map": [3, 0, 1, 2],
                "miso_ds_uart_map": [1, 2, 3, 0],
                "mosi_uart_map": [2, 3, 0, 1]},
                "missing": {}
            }
            with open(prefix + ".json", "w", encoding="utf-8") as output:
                json.dump(payload, output, indent=4)
            print(f"network JSON: {prefix}.json")
        else:
            print()
            print(
                "NO EXACT ROOT-CHIP REPLY"
            )

            #
            # Print only vaguely interesting packets,
            # not 1600 lines of noise.
            #
            interesting = [
                p for p in valid
                if (
                    p.chip_id == 1
                    or p.register_address
                    == chip_id_reg
                )
            ]

            print(
                f"interesting valid packets: "
                f"{len(interesting)}"
            )

            for p in interesting[:20]:
                print(" ", p)

    finally:

        #
        # Leave RX quiet.
        #
        try:
            pacman_base.disable_all_pacman_uart(io, iog)
        except Exception:
            pass

        io.cleanup()
        io.join()


if __name__ == "__main__":
    main()
