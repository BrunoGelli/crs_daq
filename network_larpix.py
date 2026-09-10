import warnings
warnings.filterwarnings("ignore")
import larpix
import time
import larpix.io
from runenv import runenv as RUN
import argparse
from base import config_loader
from base import network_base
from tqdm import tqdm
from base import pacman_base
from base import utility_base
from base import enforce_parallel
from base.asic_family import control_io_settings
import json
from base.utility_base import now
import logging
import sys
import os

module = sys.modules[__name__]
for var in RUN.config.keys():
    setattr(module, var, getattr(RUN, var))

_default_verbose = False
_default_controller_config = None
_update_default=False

def enforce_iterative(nc, all_network_keys, n=5, configs=None, pbar_desc='p', pbar_position=0):
    """Retry enforcement without constructing a second, wrongly typed IO."""
    last = (False, {}, all_network_keys)
    for _ in range(n + 1):
        last = enforce_parallel.enforce_parallel(
            nc, all_network_keys, pbar_desc=pbar_desc, pbar_position=pbar_position
        )
        if last[0]:
            return last
    return last

def main(verbose,\
        controller_config, \
        io_group_tiles=None,
        pacman_config=None,
        config_path=None,
        pid_logged=False,
        update_default=_update_default):
    
    pacman_configs = {}
    with open(pacman_config, 'r') as f:
        pacman_configs = json.load(f)
    control_io_group, asic_family, packet_family = control_io_settings(pacman_config)
    
    configs = {}
    with open(controller_config, 'r') as f:
        configs = json.load(f)
 
    DCONFIGS={}

    # for each io_group, perform networking     
    all_network_keys = []
    for io_group_ip_pair in pacman_configs['io_group']:
        io_group = io_group_ip_pair[0]
        tiles=None
        if not io_group_tiles is None:
            if not io_group in io_group_tiles.keys(): continue
            else:
                tiles = io_group_tiles[io_group]

        if verbose: print('Configuring io_group={}'.format(io_group))
        c = None

        config = configs[str(io_group)]
        dd=utility_base.update_json(network_config_paths_file_, io_group, config)
        if io_group != control_io_group:
            raise RuntimeError('PACMAN configuration/io_group changed during startup')
        if asic_family in ('2d', 3):
            if verbose: print('loading network_v2b') 
            c = network_base.network_v2b(
                config, tiles=tiles, io_group=io_group,
                pacman_config=pacman_config, asic_version=asic_family,
                packet_family=packet_family,
            )
        
        elif io_group_asic_version_[io_group] in [2, 'lightpix-1']:
            if verbose: print('loading network_v2a')
            c = network_base.network_v2a(config, tiles=tiles, io_group=io_group, pacman_config=pacman_config) 
            if verbose: print('done') 
        all_network_keys += enforce_parallel.get_chips_by_io_group_io_channel(config, tiles)
        
        _tiles = []
        for _, io_channels in c.network.items(): _tiles += utility_base.io_channel_list_to_tile(list(io_channels.keys()) )
        
        _update_now=False
        CONFIG=utility_base.get_from_json(default_asic_config_paths_file_,io_group)
        if update_default or CONFIG is None: 
            config_path = config_loader.write_config_to_file(c, config_path) 
            _update_now=True


        DCONFIG=None
        if _update_now: 
            dd=utility_base.update_json(default_asic_config_paths_file_, io_group, config_path)
            DCONFIG=config_path
        else:
            DCONFIG=utility_base.get_from_json(default_asic_config_paths_file_,io_group) 
        dd=utility_base.update_json(asic_config_paths_file_, io_group,DCONFIG )
        DCONFIGS[io_group]=DCONFIG

    nc = larpix.Controller()
    nc.io = larpix.io.PACMAN_IO(
        relaxed=True, config_filepath=pacman_config,
        asic_version=packet_family,
    )
    
    for io_group_ip_pair in pacman_configs['io_group']:
        io_group = io_group_ip_pair[0]
        for iog in DCONFIGS.keys():
            config_loader.load_config_from_directory(nc, DCONFIGS[iog])

        pacman_base.enable_pacman_uart_from_io_channel(nc.io, io_group, list(set([chip.io_channel for chip in nc.chips])))
    pos=0
    tag='networking...'
    if pid_logged:
        pid = os.getpid()
        tag = utility_base.get_from_process_log(pid)
        pos = enforce_parallel.tag_to_config_map[tag]
    ok, diff, unconfigured = enforce_iterative(nc, all_network_keys, configs=configs, pbar_desc=tag, pbar_position=pos)
    if not ok:
        raise RuntimeError('Unconfigured chips!', diff)
    
    if pid_logged: print('\n{} networked successfully'.format(tag))
    return c

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='store_true',  default=_default_verbose)
    parser.add_argument('--config_path', default=None, \
                        type=str, help='''Path to save configuration''')
    parser.add_argument('--controller_config', default=_default_controller_config, \
                        type=str, help='''Controller config specifying hydra network''')                  
    parser.add_argument('--pacman_config', default="io/pacman.json", \
                        type=str, help='''Config specifying PACMANs''')
    parser.add_argument('--pid_logged', action='store_true', default=False)
    parser.add_argument('--update_default', action='store_true', default=False)
    args=parser.parse_args()
    c = main(**vars(args))
