"""Functions that help with tracking of experiments"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/40_experiments/30_tracking.ipynb.

# %% auto 0
__all__ = ['get_git_hash', 'get_library_version']

# %% ../../nbs/40_experiments/30_tracking.ipynb 3
from typing import Union, List, Tuple, Literal
import pkg_resources
import subprocess
import wandb
import logging

# %% ../../nbs/40_experiments/30_tracking.ipynb 4
def get_git_hash(
    directory: str, # the directory where the git repository is located
    tracking: bool = False, # whether to directly track the git revision hash
    tracking_tool: Literal['wandb'] = 'wandb' # Currently only wandb is supported
) -> str:
    
    """ Get the git hash and optionally track """

    hash = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=directory).decode('ascii').strip()

    if tracking:
        if tracking_tool == 'wandb':
            wandb.config.update({'git_hash': hash})
        else:
            raise ValueError(f"Tracking tool {tracking_tool} is not supported")

    return hash

# %% ../../nbs/40_experiments/30_tracking.ipynb 6
def get_library_version(
    library_name: str,
    tracking: bool = False, # Whether to directly track the library version
    tracking_tool: Literal['wandb'] = 'wandb' # Currently only wandb is supported
    ) -> str:

    """ Get the version of a specified library and optionally track it """
    
    try:
        version = pkg_resources.get_distribution(library_name).version
    except pkg_resources.DistributionNotFound:
        logging.warning(f"Library '{library_name}' not found")
        return "Not installed or not found"

    if tracking:
        if tracking_tool == 'wandb':
            wandb.config.update({f'{library_name}_version': version})
        else:
            raise ValueError(f"Tracking tool {tracking_tool} is not supported")

    return version
