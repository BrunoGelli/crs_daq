# CERN runtime network configurations

This directory intentionally contains only the small IOG-to-network index.
The old eight-IOG 2x2 controller files and 64 checked-in Hydra networks were
not valid for the CERN Rev5/Hijinks bench and have been removed.

Generate the two authoritative network files in the repository root before
running `network_larpix.py`:

```bash
python hydra_v2d.py --io_group 1 --pacman_tile 7 \
  --pacman_config io/pacman_io1.json --verbose
python hydra_v3.py --config io/pacman_io2.json --io-group 2 \
  --io-channel 37 --tile 10
```

`controller_config.json` maps IOG 1 and IOG 2 to those generated files.
Generated network and ASIC configuration files are bench artifacts and should
not be committed until they have been reviewed as known-good hardware state.
