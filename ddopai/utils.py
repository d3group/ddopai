"""Some general utility functions that are used throughout the package."""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_utils/00_utils.ipynb.

# %% auto 0
__all__ = ['check_parameter_types', 'Parameter', 'MDPInfo', 'DatasetWrapper', 'DatasetWrapperMeta', 'merge_dictionaries',
           'set_param']

# %% ../nbs/00_utils/00_utils.ipynb 3
from torch.utils.data import Dataset
from typing import Union, List, Tuple, Literal, Dict
from gymnasium.spaces import Space
from .dataloaders.base import BaseDataLoader

import logging

import numpy as np

# %% ../nbs/00_utils/00_utils.ipynb 4
def check_parameter_types(
                            *args,                      # any number of parameters to be checked
                            parameter_type=np.ndarray   # the expected type for each parameter
):
    
    """
    Checks if each argument in args is of the specified type, defaulting to np.ndarray.
    """
    
    for index, arg in enumerate(args):
        if not isinstance(arg, parameter_type):
            raise TypeError(f"Argument {index+1} of {len(args)} is of type {type(arg).__name__}, expected {parameter_type.__name__}")

# %% ../nbs/00_utils/00_utils.ipynb 7
class Parameter():

    """
    Legacy, not used in the current implementation.
    """
    
    pass

# %% ../nbs/00_utils/00_utils.ipynb 8
class MDPInfo():
    """
    This class is used to store the information of the environment.
    It is based on MushroomRL (https://github.com/MushroomRL). It can be accessed by 
    agents that need the information of the environment, such as the state and action spaces.
    
    Key difference with MushroomRL is that the state and action spaces are gymnasium spaces.
    """
    
    def __init__(self,
                observation_space: Space,
                action_space: Space,  
                gamma: float,
                horizon: int,
                dt: float = 1e-1,
                backend: Literal['numpy'] = 'numpy'  # Currently only numpy is supported
            ) -> None: 

        self.observation_space = observation_space
        self.action_space = action_space
        self.gamma = gamma
        self.horizon = horizon
        self.dt = dt
        self.backend = backend

    @property
    def size(self):
        """
        Returns: The sum of the number of discrete states and discrete actions. Only works for discrete spaces.

        """
        return self.observation_space.size + self.action_space.size

    @property
    def shape(self):
        """
        Returns: The concatenation of the shape tuple of the state and action spaces.

        """
        return self.observation_space.shape + self.action_space.shape

# %% ../nbs/00_utils/00_utils.ipynb 12
class DatasetWrapper(Dataset):
    """
    This class is used to wrap a Pytorch Dataset around the ddopai dataloader
    to enable the usage of the Pytorch Dataloader during training. This way,
    agents that are trained using Pytorch without interacting with the environment
    can directly train on the data generated by the dataloader.
    
    """

    def __init__(self, 
            dataloader: BaseDataLoader, # Any dataloader that inherits from BaseDataLoader
            obsprocessors: List = None # processors (to mimic the environment processors)
            ):
        self.dataloader = dataloader
        self.obsprocessors = obsprocessors or []
    
    def __getitem__(self, idx):
        """
        Get the item at the provided idx.

        """

        # create tuple of items

        output = self.dataloader[idx]

        X = output[0]

        X = np.expand_dims(X, axis=0) # single datapoints are always returned without batch dimension, need to add for obsprocessors

        for obsprocessor in self.obsprocessors:
            X = obsprocessor(X)
        
        X = np.squeeze(X, axis=0) # remove batch dimension

        output = (X, *output[1:])
        
        return output


    def __len__(self):

        """

        Returns the length of the dataset. Depends on the state of
        the dataloader (train, val, test).

        """
        
        if self.dataloader.dataset_type == 'train':
            return self.dataloader.len_train
        elif self.dataloader.dataset_type == 'val':
            return self.dataloader.len_val
        elif self.dataloader.dataset_type == 'test':
            return self.dataloader.len_test
        else:
            raise ValueError("Dataset type must be either 'train', 'val' or 'test'")

# %% ../nbs/00_utils/00_utils.ipynb 16
class DatasetWrapperMeta(DatasetWrapper):
    """
    This class is used to wrap a Pytorch Dataset around the ddopai dataloader
    to enable the usage of the Pytorch Dataloader during training. This way,
    agents that are trained using Pytorch without interacting with the environment
    can directly train on the data generated by the dataloader.
    
    """

    def __init__(self, 
            dataloader: BaseDataLoader, # Any dataloader that inherits from BaseDataLoader
            draw_parameter_function: callable = None, # function to draw parameters from distribution
            distribution: Literal["fixed", "uniform"] | List = "fixed", # distribution for params during training, can be List for multiple parameters
            parameter_names: List[str] = None, # names of the parameters
            bounds_low: Union[int, float] | List = 0, # lower bound for params during training, can be List for multiple parameters
            bounds_high: Union[int, float] | List = 1, # upper bound for params during training, can be List for multiple parameters
            obsprocessors: List = None # processors (to mimic the environment processors)
            ):

        if isinstance(distribution, list) or isinstance(bounds_low, list) or isinstance(bounds_high, list):
            raise NotImplementedError("Multiple parameters not yet implemented")
        if obsprocessors is None:
            raise ValueError("Obsprocessors must be provided")
        
        self.distribution = [distribution]
        self.bounds_low = [bounds_low]
        self.bounds_high = [bounds_high]
        
        self.dataloader = dataloader

        self.draw_parameter = draw_parameter_function
        self.obsprocessors = obsprocessors

        self.parameter_names = parameter_names
    
    def __getitem__(self, idx):
        """
        Get the item at the provided idx.

        """

        features, demand = self.dataloader[idx] 

        features = np.expand_dims(features, axis=0) # add batch dimension as meta environments also return a batch dimension (needed for obsprocessor)

        params = {}
        for i in range(len(self.distribution)):
            param = self.draw_parameter(self.distribution[0], self.bounds_low[0], self.bounds_high[0], samples=1) # idx always gets a single sample
            params[self.parameter_names[i]] = param
        
        obs = params.copy()
        obs["features"] = features

        for obsprocessor in self.obsprocessors:
            obs = obsprocessor(obs)

        obs = np.squeeze(obs, axis=0) # remove batch dimension after observation has been processed as the pytorch dataloader adds the batch dimension

        return obs, demand, params

# %% ../nbs/00_utils/00_utils.ipynb 18
def merge_dictionaries(dict1, dict2):
    """ Merge two dictionaries. If a key is found in both dictionaries, raise a KeyError. """
    for key in dict2:
        if key in dict1:
            raise KeyError(f"Duplicate key found: {key}")
    
    # If no duplicates are found, merge the dictionaries
    merged_dict = {**dict1, **dict2}
    return merged_dict

# %% ../nbs/00_utils/00_utils.ipynb 20
def set_param(obj,
                name: str, # name of the parameter (will become the attribute name)
                input: Parameter | int | float | np.ndarray | List | Dict | None , # input value of the parameter
                shape: tuple = (1,), # shape of the parameter
                new: bool = False, # whether to create a new parameter or update an existing one
                ): 
    """
        Set a parameter for the class. It converts scalar values to numpy arrays and ensures that
        environment parameters are either of the Parameter class of Numpy arrays. If new is set to True, 
        the function will create a new parameter or update an existing one otherwise. If new is set to
        False, the function will raise an error if the parameter does not exist.
    """


    if input is None:
        param = None

    if not new:
        # get current shape of parameter
        if not hasattr(self, name):
            # if parameter is not a dict, get the shape
            raise AttributeError(f"Parameter {name} does not exist")

        if not isinstance(getattr(self, name), dict):
            shape = getattr(self, name).shape

    elif isinstance(input, Parameter):
        if input.shape != shape:
            raise ValueError("Parameter shape must be equal to the shape specified for this environment parameter")
        param = input
    
    elif isinstance(input, (int, float, np.integer, np.floating)):
        param = np.full(shape, input)

    elif isinstance(input, list):
        input = np.array(input)
        if input.shape == shape:
            param = input
        elif input.size == 1:  # Handle single-element arrays correctly
            param = np.full(shape, input.item())
        else:
            raise ValueError("Error in setting parameter. Input array must match the specified shape or be a single-element array")

    elif isinstance(input, np.ndarray):
        if input.shape == shape:
            param = input
        elif input.size == 1:  # Handle single-element arrays correctly
            param = np.full(shape, input.item())
        else:
            raise ValueError("Error in setting parameter. Input array must match the specified shape or be a single-element array")

    elif isinstance(input, dict):
        param = input

    else:
        raise TypeError(f"Input must be a Parameter, scalar, numpy array, list, or dict. Got {type(input).__name__} with value {input}")

    # set the parameter
    if new:
        if hasattr(obj, name):
            logging.warning(f"Parameter {name} already exists. Overwriting it.")
        setattr(obj, name, param)
    else:
        if not hasattr(obj, name):
            raise AttributeError(f"Parameter {name} does not exist")
        else:
            setattr(obj, name, param)
