# CERN mixed-v2d/v3 validation

The control plane is intentionally homogeneous: every command below uses one
`io/pacman_ioN.json`. Only raw recording uses aggregate `io/pacman.json`.
Run from the repository root with the bench-proven larpix-control release
(`5a69050422e82356c8faf9ad0ea3168c322d63e8`) on `PYTHONPATH`.

## Safe validation ladder

### Current hardware gate: v2d primitives only

UART ratios are persistent PACMAN state. Establish and verify the measured
v2d values before powering/networking the tile:

```bash
python tools/cern/uart_clock.py --config io/pacman_io1.json \
  --logical-channels 25 26 27 --set-expected
python tools/cern/uart_clock.py --config io/pacman_io1.json \
  --logical-channels 25 26 27
```

Expected mappings/readbacks are logical 25 → physical 21/register `0x17010`,
logical 26 → physical 22/register `0x18010`, and logical 27 → physical
23/register `0x19010`, all with value `2`. Then run only the v2d primitive:

```bash
python configure_pacman.py --pacman_config io/pacman_io1.json \
  --verbose --settle 1.0
python hydra_v2d.py --io_group 1 --pacman_tile 7 \
  --pacman_config io/pacman_io1.json --verbose
```

The root diagnostic must show downstream `[0,0,1,0]`, roots 21/61/101 must
configure, logical 28 must be skipped, and discovery must finish with zero
non-configured chips. Stop here and report the result before testing the v3 or
higher-level workflow.

Power/configure the two Rev5 boards independently:

```bash
python configure_pacman.py --pacman_config io/pacman_io1.json --verbose
python configure_pacman.py --pacman_config io/pacman_io2.json --verbose
```

Rev5 telemetry is sampled after a 0.5-second settling delay. Use
`--settle 1.0` if the first voltage readback is still transient.

Repeat the authoritative semantic-register proof (the script restores values):

```bash
unzip -q CERN_Coldbox_Codex_Handoff_2026-09-09.zip -d /tmp/cern-handoff
python /tmp/cern-handoff/CERN_Coldbox_Codex_Handoff_2026-09-09/scratch/scratch/pacman-tests/mixed_asic_register_test.py
```

Discover v2d tile 7. Logical 28 is skipped because it is dead; roots 21, 61,
and 101 should communicate and the run should finish with no non-configured
chips:

```bash
python hydra_v2d.py --io_group 1 --pacman_tile 7 \
  --pacman_config io/pacman_io1.json --verbose
```

Bootstrap the proven v3 root on logical 37 (physical UART 30), then save the
normal controller JSON:

```bash
python hydra_v3.py --config io/pacman_io2.json --io-group 2 \
  --io-channel 37 --tile 10
```

Power down safely at any point with:

```bash
run/iog/power_down.sh all
```

Network/enforce each family independently, then concurrently:

```bash
python network_larpix.py --controller_config configs/controller_config.json \
  --pacman_config io/pacman_io1.json --config_path asic_configs/iog1 --verbose
python network_larpix.py --controller_config configs/controller_config.json \
  --pacman_config io/pacman_io2.json --config_path asic_configs/iog2 --verbose
run/iog/network.sh all
```

Configure independently, then concurrently (omit the directory to use the
current configuration index):

```bash
python configure_larpix.py --pacman_config io/pacman_io1.json --verbose
python configure_larpix.py --pacman_config io/pacman_io2.json --verbose
run/iog/configure.sh all
```

Record one 20-second mixed raw file. Do not pass `--packet`:

```bash
python record_data.py --pacman_config io/pacman.json --runtime 20 \
  --file_count 1 --filename cern-mixed-20s.h5 --ignore_embed
```

Inspect the raw message headers and confirm both `io_group` values before
family-aware offline decoding. Decode IOG 1 payloads as `Packet_v2` and IOG 2
payloads as `Packet_v3`; never feed the aggregate file to one parsed packet
family.

## Expected v2d root bootstrap diagnostic

The FSD donor root return path is intentionally `enable_posi=[0,0,0,1]` and
`enable_piso_downstream=[0,0,1,0]`. Seeing downstream `[1,0,0,0]` identifies
the obsolete 2x2 UART orientation and is a failure. `configure_pacman.py` and
the network loaders also program the Rev5 sync mask and all 32 packet-delay
registers, so each networking command can establish its required PACMAN-side
infrastructure explicitly.

## v2d export and physical-label validation gate

The successful donor run programmed root IDs 21, 61, 101, and 151. It proved
communication, but did **not** prove that programmed ID 101 was physical tile
position 101. Jack's 10x16 geometry defines position `11 + 10*column + row`
and physical roots 21, 61, 111, and 151. Connector-to-root correspondence is
not inferred: default discovery retains donor-programmed IDs, while a
physical-label run requires an explicit operator-confirmed map.

First reproduce the successful discovery and export without changing IDs:

```bash
rm -f iog_1-tile_7-hydra-network.json
python hydra_v2d.py --io_group 1 --pacman_tile 7 \
  --pacman_config io/pacman_io1.json --verbose
python -m json.tool iog_1-tile_7-hydra-network.json >/dev/null
```

Expected stages are reported separately: traversal reaches zero
non-configured chips; topology validation succeeds; JSON export succeeds.
The JSON must contain channels 25, 26, and 27 and deliberately omit dead
logical channel 28.

Only after connector order has been confirmed, power-cycle/reconfigure the
tile and re-run with all three live connector assignments stated. Replace the
example values below if the confirmed connector order differs:

```bash
python hydra_v2d.py --io_group 1 --pacman_tile 7 \
  --pacman_config io/pacman_io1.json --verbose \
  --file_prefix iog_1-tile_7-physical \
  --physical-root-map 25:21 \
  --physical-root-map 26:61 \
  --physical-root-map 27:111
```

The command rejects incomplete connector maps, duplicate roots, position 101
as a physical root, and values outside the declared physical-root set. It
writes the requested IDs to ASICs initially addressed as chip 1; this is a
separate hardware operation, not relabeling of an old JSON file.
