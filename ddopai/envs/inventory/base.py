"""Base environment with some basic funcitons"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../../nbs/20_environments/21_envs_inventory/10_base_inventory_env.ipynb.

# %% auto 0
__all__ = ['BaseInventoryEnv']

# %% ../../../nbs/20_environments/21_envs_inventory/10_base_inventory_env.ipynb 3
from abc import ABC, abstractmethod
from typing import Union, Tuple, List

from ..base import BaseEnvironment
from ...utils import Parameter, MDPInfo
from ...dataloaders.base import BaseDataLoader
from ...loss_functions import pinball_loss

import gymnasium as gym

import numpy as np
import time

# %% ../../../nbs/20_environments/21_envs_inventory/10_base_inventory_env.ipynb 4
class BaseInventoryEnv(BaseEnvironment):
    """
    Base class for inventory management environments. This class inherits from BaseEnvironment.
    
    """

    def __init__(self, 

        ## Parameters for Base env:
        mdp_info: MDPInfo, #
        postprocessors: list[object] | None = None,  # default is empty list
        mode: str = "train", # Initial mode (train, val, test) of the environment
        return_truncation: str = True, # whether to return a truncated condition in step function
        dataloader: BaseDataLoader = None, # dataloader for the environment
        horizon_train: int = 100, # horizon for training mode
        
        # Parameters common in all inventory environments
        underage_cost: Union[np.ndarray, Parameter, int, float] = 1, # underage cost per unit
        overage_cost: Union[np.ndarray, Parameter, int, float] = 0, # overage cost per unit (zero in most cases)

        ) -> None:

        self.dataloader = dataloader
        
        self.set_param("underage_cost", underage_cost, shape=(self.num_SKUs[0],), new=True)
        self.set_param("overage_cost", overage_cost, shape=(self.num_SKUs[0],), new=True)

        super().__init__(mdp_info=mdp_info, postprocessors = postprocessors,  mode = mode, return_truncation=return_truncation, horizon_train=horizon_train)
    
    def set_observation_space(self,
                            shape: tuple, # shape of the dataloader features
                            low: Union[np.ndarray, float] = -np.inf, # lower bound of the observation space
                            high: Union[np.ndarray, float] = np.inf, # upper bound of the observation space
                            samples_dim_included = True # whether the first dimension of the shape input is the number of samples
                            ) -> None:
        
        '''
        Set the observation space of the environment.
        This is a standard function for simple observation spaces. For more complex observation spaces,
        this function should be overwritten. Note that it is assumped that the first dimension
        is n_samples that is not relevant for the observation space.

        '''

        # To handle cases when no external information is available (e.g., parametric NV)
        
        if shape is None:
            self.observation_space = None

        else:
            if not isinstance(shape, tuple):
                raise ValueError("Shape must be a tuple.")
            
            if samples_dim_included:
                shape = shape[1:] # assumed that the first dimension is the number of samples

            self.observation_space = gym.spaces.Box(low=low, high=high, shape=shape, dtype=np.float32)

    def set_action_space(self,
                            shape: tuple, # shape of the dataloader target
                            low: Union[np.ndarray, float] = -np.inf, # lower bound of the observation space
                            high: Union[np.ndarray, float] = np.inf, # upper bound of the observation space
                            samples_dim_included = True # whether the first dimension of the shape input is the number of samples
                            ) -> None:
        
        '''
        Set the action space of the environment.
        This is a standard function for simple action spaces. For more complex action spaces,
        this function should be overwritten. Note that it is assumped that the first dimension
        is n_samples that is not relevant for the action space.
        '''

        if not isinstance(shape, tuple):
            raise ValueError("Shape must be a tuple.")
        
        if samples_dim_included:
            shape = shape[1:] # assumed that the first dimension is the number of samples

        self.action_space = gym.spaces.Box(low=low, high=high, shape=shape, dtype=np.float32)
    
    def get_observation(self):
        
        """
        Return the current observation. This function is for the simple case where the observation
        is only an x,y pair. For more complex observations, this function should be overwritten.

        """

        X_item, Y_item = self.dataloader[self.index]

        return X_item, Y_item
    
    def reset(self,
        start_index: int | str = None, # index to start from
        state: np.ndarray = None # initial state
        ) -> Tuple[np.ndarray, bool]:

        """
        Reset function for the Newsvendor problem. It will return the first observation and demand.
        For val and test modes, it will by default reset to 0, while for the train mode it depends
        on the paramter "horizon_train" whether a random point in the training data is selected or 0
        """

        truncated = self.reset_index(start_index)

        print("index:", self.index)

        observation, self.demand = self.get_observation()
        
        return observation

