"""Construction and validation helpers for CERN controller network JSON."""

import json

UART_MAPS = {
    "miso_us_uart_map": [3, 0, 1, 2],
    "miso_ds_uart_map": [1, 2, 3, 0],
    "mosi_uart_map": [2, 3, 0, 1],
}


def root_only_network(io_group, io_channel, chip_id, name, asic_version,
                      layout="10x16"):
    """Build a controller-compatible external-root-to-ASIC network."""
    network = {
        str(io_group): {
            str(io_channel): {
                "nodes": [
                    {
                        "chip_id": "ext",
                        "miso_us": [None, None, None, chip_id],
                        "root": True,
                    },
                    {
                        "chip_id": chip_id,
                        "miso_us": [None, None, None, None],
                    },
                ]
            }
        }
    }
    network.update(UART_MAPS)
    return {
        "_config_type": "controller",
        "name": name,
        "asic_version": asic_version,
        "layout": layout,
        "network": network,
        "missing": {},
    }


def validate_external_roots(config_path):
    """Reject malformed root graphs before larpix ``init_network`` runs."""
    with open(config_path, encoding="utf-8") as infile:
        payload = json.load(infile)
    network = payload.get("network", {})
    checked = 0
    for io_group, channels in network.items():
        if not str(io_group).isdigit():
            continue
        for io_channel, channel in channels.items():
            nodes = channel.get("nodes", [])
            external = [node for node in nodes if node.get("chip_id") == "ext"]
            if len(external) != 1 or not external[0].get("root"):
                raise ValueError(
                    f"{config_path}: {io_group}-{io_channel} must contain "
                    "one external root node"
                )
            links = [value for value in external[0].get("miso_us", [])
                     if value is not None]
            chip_ids = {node.get("chip_id") for node in nodes
                        if node.get("chip_id") != "ext"}
            if len(links) != 1 or links[0] not in chip_ids:
                raise ValueError(
                    f"{config_path}: external root for {io_group}-{io_channel} "
                    "must point to exactly one ASIC node"
                )
            checked += 1
    if not checked:
        raise ValueError(f"{config_path}: no controller network channels found")
    return payload
