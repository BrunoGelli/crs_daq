# CERN mixed-v2d/v3 validation

The control plane is intentionally homogeneous: every command below uses one
`io/pacman_ioN.json`. Only raw recording uses aggregate `io/pacman.json`.
Run from the repository root with the bench-proven larpix-control release
(`5a69050422e82356c8faf9ad0ea3168c322d63e8`) on `PYTHONPATH`.

## Safe validation ladder

Power/configure the two Rev5 boards independently:

```bash
python configure_pacman.py --pacman_config io/pacman_io1.json --verbose
python configure_pacman.py --pacman_config io/pacman_io2.json --verbose
```

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
