# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/30_experiment_functions/20_meta_experiment_functions.ipynb.

# %% auto 0
__all__ = ['set_warnings', 'prep_experiment', 'init_wandb', 'track_libraries_and_git', 'import_config',
           'transfer_lag_window_to_env', 'get_ddop_data', 'download_data', 'set_indices', 'set_up_env',
           'set_up_earlystoppinghandler', 'prep_and_run_test', 'clean_up', 'select_agent']

# %% ../nbs/30_experiment_functions/20_meta_experiment_functions.ipynb 3
from abc import ABC, abstractmethod
from typing import Union, List, Tuple, Dict, Literal
import logging
from datetime import datetime  
import numpy as np
import sys
import os
import yaml
import pickle
import warnings
import torch

from .tracking import get_git_hash, get_library_version
from .agents.class_names import AGENT_CLASSES
from .dataloaders.tabular import XYDataLoader
from .datasets import DatasetLoader
from .experiment_functions import EarlyStoppingHandler, test_agent

import wandb

import gc

import importlib

from tqdm import tqdm, trange

# Think about how to handle mushroom integration.
from mushroom_rl.core import Core

# %% ../nbs/30_experiment_functions/20_meta_experiment_functions.ipynb 5
def set_warnings (logging_level):

    """ Set warnings to be ignored for the given logging level or higher."""

    if logging.getLogger().isEnabledFor(logging_level):
        warnings.filterwarnings("ignore", category=UserWarning, message=".*Box bound precision lowered by casting to float32.*")
        warnings.filterwarnings("ignore", category=UserWarning, message=".*TypedStorage is deprecated.*")
        warnings.filterwarnings("ignore", category=FutureWarning, message=".*You are using `torch.load` with `weights_only=False`.*")

# %% ../nbs/30_experiment_functions/20_meta_experiment_functions.ipynb 7
def prep_experiment(
    project_name: str,
    libraries_to_track: List[str] = ["ddopnew"],
    config_train_name: str = "config_train",
    config_agent_name: str = "config_agent",
    config_env_name: str = "config_env",
):
    """ First stpes to always execute when starting an experiment (using wandb for tracking)"""

    init_wandb(project_name)
    track_libraries_and_git(libraries_to_track)

    config_train = import_config(config_train_name)
    config_agent = import_config(config_agent_name) # General config file containing all agent parameters
    config_env = import_config(config_env_name)

    AgentClass = select_agent(config_train["agent"]) # Select agent class and import dynamically
    agent_name = config_train["agent"]
    config_agent = config_agent[config_train["agent"]] # Get parameters for specific agent
    
    transfer_lag_window_to_env(config_env, config_agent) 

    wandb.config.update(config_train)
    wandb.config.update(config_agent)
    wandb.config.update(config_env)

    return config_train, config_agent, config_env, AgentClass, agent_name

# %% ../nbs/30_experiment_functions/20_meta_experiment_functions.ipynb 8
def init_wandb(project_name: str): #

    """ init wandb """

    wandb.init(
        project=project_name,
        name = f"{project_name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    )

# %% ../nbs/30_experiment_functions/20_meta_experiment_functions.ipynb 9
def track_libraries_and_git(    libraries_to_track: List[str],
                                tracking: bool = True,
                                tracking_tool = "wandb", # Currenty only wandb is supported
                                ) -> None:
    
    """
    Track the versions of the libraries and the git hash of the repository.

    """

    for lib in libraries_to_track:
        version = get_library_version(lib, tracking=tracking, tracking_tool=tracking_tool)
        logging.info(f"{lib}: {version}")
    git_hash = get_git_hash(".", tracking=tracking, tracking_tool=tracking_tool)
    logging.info(f"Git hash: {git_hash}")

# %% ../nbs/30_experiment_functions/20_meta_experiment_functions.ipynb 10
def import_config(  filename: str, # Name of the file, must be a yaml file
                    path: str = None # Optional path to the file if it is not in the current directory
                    ) -> Dict:
    
    """
    Import a config file in YAML format

    """

    # Check if filename has an extension
    if '.' in filename:
        extension = filename.split(".")[-1]
    else:
        extension = ''

    if not extension:
        filename += ".yaml"
    elif extension not in ["yaml", "yml"]:
        raise ValueError("The configuration file must have a .yaml or .yml extension.")


    if path is not None:
        full_path = os.path.join(path, filename)
    else:
        full_path = filename
    

    # Check if the file exists
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"The configuration file '{full_path}' does not exist.")

    with open(full_path, "r") as stream:
        try:
            config = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise yaml.YAMLError(f"Error parsing YAML file '{full_path}': {exc}")
    
    logging.info(f"Configuration file '{filename}' successfully loaded.")
    logging.debug(f"Configuration: {config}")

    return config

# %% ../nbs/30_experiment_functions/20_meta_experiment_functions.ipynb 11
def transfer_lag_window_to_env(config_env: Dict, #
                                config_agent: Dict
                                ) -> None:
    
    """
    Transfer the lag window from the agent configuration to the environment configuration

    """
    
    if "lag_window" in config_agent.keys():
        if isinstance(config_agent["lag_window"], int):
            config_env["lag_window_params"]["lag_window"] = config_agent["lag_window"]
        else:
            raise ValueError("The lag window must be an integer.")
        del config_agent["lag_window"]
    else:
        logging.warning("No lag window specified in the agent configuration. Keeping value from env config")

# %% ../nbs/30_experiment_functions/20_meta_experiment_functions.ipynb 13
def get_ddop_data(
    config_env: Dict,
    overwrite: bool = False
    ) -> Tuple:

    """ Standard function to load data provided by the ddop package """
    
    data = download_data(config_env, overwrite)

    val_index_start, test_index_start = set_indices(config_env, data[0])

    return data, val_index_start, test_index_start


# %% ../nbs/30_experiment_functions/20_meta_experiment_functions.ipynb 14
def download_data(  config_env: Dict,
                    overwrite: bool = False #
                    ) -> Tuple:

    """ Download standard dataset from ddop repository using the DatasetLoader class """

    datasetloader = DatasetLoader()

    data = datasetloader.load_dataset(
        dataset_type = config_env["dataset_type"],
        dataset_number = config_env["dataset_number"],
        overwrite=False)

    data_tuple = data["data_raw_features"], data["data_raw_target"]

    return data_tuple

# %% ../nbs/30_experiment_functions/20_meta_experiment_functions.ipynb 15
def set_indices(config_env: Dict, #
                X: np.ndarray 
) -> Tuple:

    """ Set the indices for the validation and test set """

    val_index_start = len(X) - config_env["size_val"] - config_env["size_test"]
    test_index_start = len(X) - config_env["size_test"]

    return val_index_start, test_index_start

# %% ../nbs/30_experiment_functions/20_meta_experiment_functions.ipynb 17
def set_up_env(
    env_class,
    raw_data: Tuple, #
    val_index_start: int,
    test_index_start: int,
    config_env: Dict,
    postprocessors: List,
) -> object:
    
    """ Set up the environment """

    dataloader = XYDataLoader(  X = raw_data[0],
                                Y = raw_data[1],
                                val_index_start = val_index_start,
                                test_index_start = test_index_start,
                                lag_window_params = config_env["lag_window_params"],
                                normalize_features = {'normalize': config_env["normalize_features"], 'ignore_one_hot': True})

    environment = env_class(
        dataloader = dataloader,
        postprocessors = postprocessors,
        **config_env["env_kwargs"]
    )

    return environment

# %% ../nbs/30_experiment_functions/20_meta_experiment_functions.ipynb 19
def set_up_earlystoppinghandler(config_train: Dict) -> object: #

    """ Set up the early stopping handler """

    # check if config_train has either early_stopping_patience or early_stopping_warmup
    if "early_stopping_patience" in config_train or "early_stopping_warmup" in config_train:
        warmup = config_train["early_stopping_warmup"] if "early_stopping_warmup" in config_train else 0
        patience = config_train["early_stopping_patience"] if "early_stopping_patience" in config_train else 0

        earlystoppinghandler = EarlyStoppingHandler(warmup=warmup, patience=patience)
    else:
        earlystoppinghandler = None

    return earlystoppinghandler

# %% ../nbs/30_experiment_functions/20_meta_experiment_functions.ipynb 21
def prep_and_run_test(
    agent,
    environment,
    agent_dir: str,
    save_dataset: bool = True,
    dataset_dir: str = None,
    tracking = "wandb"):
    
    """
    Test the agent in the environment.
    """

    if save_dataset:
        if dataset_dir is None:
            raise ValueError("If save_dataset is True, dataset_dir must be specified.")

    # load parameters of agent
    agent.load(agent_dir)

    # Set agent and environment to test mode
    agent.eval()
    environment.test()

    # Run test episode
    output = test_agent(
        agent,
        environment,
        return_dataset=save_dataset,
        tracking=tracking
    )

    # Save dataset
    if save_dataset:

        R, J, dataset = output

        if not os.path.exists(dataset_dir):
            os.mkdir(dataset_dir)
        else:
            raise ValueError("Path to save dataset already exists") # it should never exist since run_id is usually part or path and unique
        
        dir = os.path.join(dataset_dir, "dataset_test.pkl")

        with open (os.path.join(dir), "wb") as f:
            pickle.dump(dataset, f)

        artifact = wandb.Artifact("transition_test_set", type="dataset")

        artifact.add_file(os.path.join(dir))

        wandb.run.log_artifact(artifact)
    
    else:

        R, J = output

    logging.info(f"final evaluation on test set: R = {np.round(R, 10)} J = {np.round(J, 10)}")



# %% ../nbs/30_experiment_functions/20_meta_experiment_functions.ipynb 23
def clean_up(agent, environment):

    """ Clean up agent and environment to free up GPU memory """
    
    # Delete agent and environment to free up GPU memory
    del agent
    del environment

    # Force garbage collection
    gc.collect()

    # Clear GPU cache
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    wandb.finish()

    return None, None

# %% ../nbs/30_experiment_functions/20_meta_experiment_functions.ipynb 27
def select_agent(agent_name: str) -> type: #
    """ Select an agent class from a list of agent names and return the class"""
    if agent_name in AGENT_CLASSES:
        module_path, class_name = AGENT_CLASSES[agent_name].rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    else:
        raise ValueError(f"Unknown agent name: {agent_name}")
