"""ASIC-family policy shared by CERN control processes.

Chip versions select a larpix ``Configuration`` class; packet families select
PACMAN payload serialization.  They are deliberately separate concepts.
"""

import json

SUPPORTED_ASIC_FAMILIES = ("2d", 3)


def normalize_asic_family(value):
    """Return the canonical larpix chip version (``"2d"`` or ``3``)."""
    if value == "2d":
        return "2d"
    if value == 3 or value == "3":
        return 3
    raise ValueError(f"Unsupported CERN ASIC family: {value!r}")


def packet_family_for_asic(value):
    """Map a chip/configuration family to its PACMAN packet family."""
    family = normalize_asic_family(value)
    return 2 if family == "2d" else 3


def uart_clock_ratio_for_asic(value):
    """Return the bench-proven persistent PACMAN UART ratio for a family."""
    family = normalize_asic_family(value)
    return 2 if family == "2d" else 1


def single_io_group(pacman_config):
    """Validate and return the IOG from a one-PACMAN control configuration."""
    pairs = pacman_config.get("io_group", [])
    if len(pairs) != 1:
        raise ValueError(
            "Control operations require exactly one PACMAN/io_group; "
            "use io/pacman.json only for raw acquisition"
        )
    return int(pairs[0][0])


def family_for_io_group(io_group, run_config_path="RUN_CONFIG.json"):
    """Read the authoritative IOG-to-family assignment from RUN_CONFIG."""
    with open(run_config_path, encoding="utf-8") as infile:
        mapping = json.load(infile)["io_group_asic_version_"]
    try:
        return normalize_asic_family(mapping[str(int(io_group))])
    except KeyError as error:
        raise KeyError(f"No ASIC family configured for io_group {io_group}") from error


def control_io_settings(pacman_config_path, run_config_path="RUN_CONFIG.json"):
    """Return ``(io_group, chip_family, packet_family)`` for control."""
    with open(pacman_config_path, encoding="utf-8") as infile:
        io_group = single_io_group(json.load(infile))
    family = family_for_io_group(io_group, run_config_path)
    return io_group, family, packet_family_for_asic(family)
