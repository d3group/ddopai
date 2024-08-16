# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/40_base_agents/10_base_agents.ipynb.

# %% auto 0
__all__ = ['BaseAgent']

# %% ../../nbs/40_base_agents/10_base_agents.ipynb 4
from abc import ABC, abstractmethod
from typing import Union, Optional, List, Tuple
import numpy as np

from ..envs.base import BaseEnvironment
from ..utils import MDPInfo, Parameter
import numbers

# # TEMPORARY
# from sklearn.utils.validation import check_array
# import numbers

# %% ../../nbs/40_base_agents/10_base_agents.ipynb 5
class BaseAgent():

    """  
    Base class for all agents to enforce a common interface. See below for more detailed description of the requriements.

    """

    train_mode = "direct_fit" # or "epochs_fit" or "env_interaction"
    
    def __init__(self,
                    environment_info: MDPInfo,
                    obsprocessors: list[object] | None = None,  # default is empty list
                    agent_name: str | None = None
                 ):

        self.obsprocessors = obsprocessors or []

        self.environment_info = environment_info
        self.mode = "train"
        self.print = False  # Can be used for debugging
        self.receive_batch_dim = False

        self.agent_name = agent_name

    def draw_action(self, observation: np.ndarray) -> np.ndarray: #

        """
        Main interfrace to the environemnt. Applies preprocessors to the observation.
        Internal logic of the agent to be implemented in draw_action_ method.
        """

        observation = self.add_batch_dim(observation)

        for obsprocessor in self.obsprocessors:
            observation = obsprocessor(observation)

        action = self.draw_action_(observation)
        
        return action

    @abstractmethod
    def draw_action_(self, observation: np.ndarray) -> np.ndarray: #
        """Generate an action based on the observation - this is the core method that needs to be implemented by all agents."""
        pass

    def add_obsprocessor(self, obsprocessor: object): # pre-processor object that can be called via the "__call__" method
        """Add a preprocessor to the agent"""
        self.obsprocessors.append(obsprocessor)

    def train(self):
        """Set the internal state of the agent to train"""
        self.mode = "train"
        
    def eval(self):
        """
        Set the internal state of the agent to eval. Note that for agents we do not differentiate between val and test modes.

        """
        self.mode = "eval"
    
    def add_batch_dim(self, input: np.ndarray) -> np.ndarray: #
        
        """
        Add a batch dimension to the input array if it doesn't already have one.
        This is necessary because most environments do not have a batch dimension, but agents typically expect one.
        If the environment does have a batch dimension, the agent can set the receive_batch_dim attribute to True to skip this step.

        """

        if self.receive_batch_dim:
            # If the batch dimension is expected, return the input as is
            return input
        else:
            # Add a batch dimension by expanding the dimensions of the input
            return np.expand_dims(input, axis=0)
        
    def save(self):
        """Save the agent's parameters to a file."""
        raise NotImplementedError("This agent does not have a save method implemented.")

    def load(self):
        """Load the agent's parameters from a file."""
        raise NotImplementedError("This agent does not have a load method implemented.")

    @staticmethod
    def update_model_params(default_params: dict, custom_params: dict) -> dict: #
        """ override default parameters with custom parameters in a dictionary"""
        updated_params = default_params.copy()
        updated_params.update(custom_params)
        return updated_params

    @staticmethod
    def convert_to_numpy_array(
        input: np.ndarray | List | float | int | Parameter | None #
    ):

        """convert input to numpy array or keep as Parameter"""

        if isinstance(input, np.ndarray):
            return input
        elif isinstance(input, (list, numbers.Number)):
            return np.array(input)
        elif isinstance(input, Parameter):
            return input
        else:
            raise ValueError("Input type not recognized.")

    @staticmethod
    def convert_recursively_to_int(
        input = List | Tuple, #
    ) -> List | Tuple:

        """convert all elements of a list or tuple to int"""

        if isinstance(input, list):
            return [BaseAgent.convert_recursively_to_int(item) for item in input]
        elif isinstance(input, tuple):
            return tuple(BaseAgent.convert_recursively_to_int(item) for item in input)
        else:
            # If it's not a list or tuple, convert to int directly
            return int(input)
