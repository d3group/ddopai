# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/20_base_env/10_base_env.ipynb.

# %% auto 0
__all__ = ['BaseEnvironment']

# %% ../../nbs/20_base_env/10_base_env.ipynb 3
import gymnasium as gym
from abc import ABC, abstractmethod
from typing import Union
import numpy as np

from ..utils import MDPInfo
from ..utils import Parameter
import time

# %% ../../nbs/20_base_env/10_base_env.ipynb 4
class BaseEnvironment(gym.Env, ABC):

    """

    Base class for environments enforcing a common interface.
    """

    def __init__(self,
                    mdp_info: MDPInfo, # MDPInfo object to ensure compatibility with the agents
                    postprocessors: list[object] | None = None,  # default is empty list
                    mode: str = "train", # Initial mode (train, val, test) of the environment
                    return_truncation: str = True # whether to return a truncated condition in step function
                    ) -> None: #

        super().__init__()

        self.return_truncation = return_truncation

        self._mode = mode
        self._mdp_info = mdp_info
        
        if mode == "train": 
            self.train()
        elif mode == "val":
            self.val()
        elif mode == "test":
            self.test()
        else:
            raise ValueError("mode must be 'train', 'val', or 'test'")

        self.postprocessors = postprocessors or []

    def set_param(self,
                        name: str, # name of the parameter (will become the attribute name)
                        input: Parameter | float | np.ndarray, # input value of the parameter
                        shape: tuple = (1,), # shape of the parameter
                        new: bool = False # whether to create a new parameter or update an existing one
                        ) -> None: #
        
        """
        Set a parameter for the environment. It converts scalar values to numpy arrays and ensures that
        environment parameters are either of the Parameter class of Numpy arrays. If new is set to True, 
        the function will create a new parameter or update an existing one otherwise. If new is set to
        False, the function will raise an error if the parameter does not exist.
        """

        # check if input is a valid type
        if isinstance(input, Parameter):
            if input.shape != shape:
                raise ValueError("Parameter shape must be equal to the shape specified for this environment parameter")
            param = input
        
        elif isinstance(input, (int, float)):
            param = np.full(shape, input)

        elif isinstance(input, list):
            input = np.array(input)
            if input.shape == shape:
                param = input
            elif input.size == 1:  # Handle single-element arrays correctly
                param = np.full(shape, input.item())
            else:
                raise ValueError("Input array must match the specified shape or be a single-element array")

        elif isinstance(input, np.ndarray):
            if input.shape == shape:
                param = input
            elif input.size == 1:  # Handle single-element arrays correctly
                param = np.full(shape, input.item())
            else:
                raise ValueError("Input array must match the specified shape or be a single-element array")
        else:
            raise TypeError("Input must be a Parameter, scalar, or numpy array")

        # set the parameter
        if new:
            if hasattr(self, name):
                logging.warning(f"Parameter {name} already exists in this environment. Overwriting it.")
            setattr(self, name, param)

            
        else:
            # check if parameter already exists
            if not hasattr(self, name):
                raise AttributeError(f"Parameter {name} does not exist in this environment")
            else:
                getattr(self, name).set(param)

    def return_truncation_handler(self, observation, reward, terminated, truncated, info):
        """ 
        Handle the return_truncation attribute of the environment. This function is called by the step function

        """

        if self.return_truncation:
            return observation, reward, terminated, truncated, info
        else:
            return observation, reward, terminated, info

    def step(self, action):
        
        """
        Step function of the environment. Do not overwrite this function. 
        Instead, write the step_ function. Note that the postprocessor is applied here.

        """

        ## apply postprocessor
        for postprocessor in self.postprocessors:
            action = postprocessor(action)

        observation, reward, terminated, truncated, info = self.step_(action)

        return self.return_truncation_handler(observation, reward, terminated, truncated, info)
    
    def add_postprocessor(self, postprocessor: object): # post-processor object that can be called via the "__call__" method
        """Add a postprocessor to the agent"""
        self.postprocessors.append(postprocessor)

    @staticmethod
    def step_(self, action):
        """
        Step function of the environment. It is a wrapper around the step function that handles the return_truncation
        attribute of the environment. It must return the following: observation, reward, terminated, truncated, info

        """
        pass


    @property
    def mdp_info(self):
        """
        Returns: The MDPInfo object of the environment.

        """
        return self._mdp_info

    @property
    def info(self):
        """
        Returns: Alternative call to the method for mushroom_rl.

        """
        return self.mdp_info

    @property
    def mode(self):
        """
        Returns: A string with the current mode (train, test val) of the environment.

        """
        return self._mode

    @abstractmethod
    def set_action_space(self):
        """
        Set the action space of the environment.

        """
        pass

    @abstractmethod
    def set_observation_space(self):
        """
        Set the observation space of the environment.
        In general, this can be also a dict space, but the agent must have the appropriate pre-processor.

        """
        pass

    @abstractmethod
    def get_observation(self):
        """
        Return the current observation. Typically constructed from the output of the dataloader and 
        internal dynamics (such as inventory levels, pipeline vectors, etc.) of the environment.

        """
        pass

    @abstractmethod
    def reset(self):
        """
        Reset the environment. This function must be provided, using the function self.reset_index() to 
        handle indexing. It needs to account for the current training mode train, val, or test and handle
        the horizon_train param. See the reset function for the NewsvendorEnv for an example.

        """
        pass
    
    def set_index(self, index=None):
        
        """
        Handle the index of the environment.

        """

        if index is not None:
            self.index = index
        else:
            self.index += 1
        
        truncated = True if self.index >= self.max_index_episode else False
        
        return truncated

    def reset_index(self,
        start_index: Union[int,str]):

        """

        Reset the index of the environment. If start_index is an integer, the index is set to this value. If start_index is "random",
        the index is set to a random integer between 0 and the length of the training data.

        """
 
        if start_index=="random":
            if self.mode == "train":
                if self.dataloader.len_train is not None and self.dataloader.len_train > self.mdp_info.horizon:
                    random_index = np.random.choice(self.dataloader.len_train-self.mdp_info.horizon)
                else:
                    random_index = 0
                self.start_index = random_index 
            else:
                raise ValueError("start_index cannot be 'random' in val or test mode")
        elif isinstance(start_index, int):
            self.start_index = start_index
        else:
            raise ValueError("start_index must be an integer or 'random'")

        self.max_index = self.dataloader.len_train if self.mode == "train" else self.dataloader.len_val if self.mode == "val" else self.dataloader.len_test
        # self.max_index -= 1
        self.max_index_episode = np.minimum(self.max_index, self.start_index+self.mdp_info.horizon)
    
        truncated = self.set_index(self.start_index) # assuming we only start randomly during training.
        
        return truncated

    def update_mdp_info(self, gamma=None, horizon=None):
        
        """
        Update the MDP info of the environment.

        """
        if gamma is not None:
            self._mdp_info.gamma = gamma
        if horizon is not None:
            self._mdp_info.horizon = horizon

    def train(self, update_mdp_info=True):
        """
        Set the environment in training mode by both setting the internal state self._train and the dataloader. 
        If the horizon is set to "use_all_data", the horizon is set to the length of the training data, otherwise
        it is set to the horizon_train attribute of the environment. Finally, the function updates the MDP info
        and resets with the new state.

        """
        self._mode = "train"

        if hasattr(self, "dataloader"):
            self.dataloader.train()

            if hasattr(self, "horizon_train"):
                if self.horizon_train == "use_all_data":
                    horizon = self.dataloader.len_train
                else:
                    horizon = self.horizon_train
        else:
            horizon = self.mdp_info.horizon

        if update_mdp_info:
            self.update_mdp_info(gamma=self.mdp_info.gamma, horizon=horizon)

        self.reset()
    
    def val(self, update_mdp_info=True):
        """
        Set the environment in validation mode by both setting the internal state self._val and the dataloader.
        The horizon of val is always set to the length of the validation data. Finally, the function updates the MDP info
        and resets with the new state.

        """
        self._mode = "val"

        if hasattr(self, "dataloader"):
            self.dataloader.val()
            horizon = self.dataloader.len_val
        else:
            horizon = self.mdp_info.horizon

        if update_mdp_info:
            self.update_mdp_info(gamma=self.mdp_info.gamma, horizon=horizon)

        self.reset()

    def test(self, update_mdp_info=True):
        """
        Set the environment in testing mode by both setting the internal state self._test and the dataloader.
        The horizon of test is always set to the length of the test data. Finally, the function updates the MDP info
        and resets with the new state.

        """
        self._mode = "test"

        if hasattr(self, "dataloader"):
            self.dataloader.test()
            horizon = self.dataloader.len_test
        else:
            horizon = self.mdp_info.horizon

        if update_mdp_info:
            self.update_mdp_info(gamma=self.mdp_info.gamma, horizon=horizon)

        self.reset()

    def set_return_truncation(self, return_truncation: bool): # whether or not to return the truncated condition in the step function
        
        """
        Set the return_truncation attribute of the environment.
        """
        
        self.return_truncation = return_truncation

    def stop(self):
        """
        Stop the environment. This function is used to ensure compatibility with the Core of mushroom_rl.

        """
        pass

