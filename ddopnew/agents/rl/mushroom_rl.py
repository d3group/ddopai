# AUTOGENERATED! DO NOT EDIT! File to edit: ../../../nbs/51_RL_agents/10_mushroom_base_agent.ipynb.

# %% auto 0
__all__ = ['MushroomBaseAgent']

# %% ../../../nbs/51_RL_agents/10_mushroom_base_agent.ipynb 3
import logging

# set logging level to INFO
logging.basicConfig(level=logging.INFO)

from abc import ABC, abstractmethod
from typing import Union, Optional, List, Tuple
import numpy as np
import os

from ..base import BaseAgent
from ...utils import MDPInfo, Parameter

import torch
import torch.nn.functional as F

import time

# %% ../../../nbs/51_RL_agents/10_mushroom_base_agent.ipynb 4
class MushroomBaseAgent(BaseAgent):

    """
    Base class for Agents that integrate MushroomRL agents.
    """

    train_mode = "env_interaction"
    dropout = True # always keep in True for mushroom_RL, dropout is not desired set drop_prob=0.0
    
    def __init__(self, 
            environment_info: MDPInfo,
            obsprocessors: Optional[List] = None,     # default: []
            device: str = "cpu", # "cuda" or "cpu"
            agent_name: str | None = None
            ):

        self.device = device

        self.network_list, self.actor, self.critic = self.get_network_list(set_actor_critic_attributes=True)

        super().__init__(environment_info = environment_info, obsprocessors = obsprocessors, agent_name = agent_name)

        self.transfer_obs_processors_to_mushroom_agent()

    def transfer_obs_processors_to_mushroom_agent(self):
    
        """ Transfer the obs-processors to the MushroomRL agent preprocessors"""

        for obsprocessor in self.obsprocessors:
            self.add_obsprocessor(obsprocessor)
        self.obsprocessors = []

    def add_obsprocessor(self, obsprocessor: object): 
        """Add an obsprocessor to the agent - overwrites the base
        class method to add the obsprocessor to the MushroomRL agent
        as preprocessor. Postprocessors stay with the base class"""
        self.agent.add_preprocessor(obsprocessor)

    @property
    def preprocessors(self):

        """ Return the obsprocessors of the agent,
        which are the preprocessors of the MushroomRL agent """

        return self.agent.preprocessors

    @abstractmethod
    def set_model(self, input_shape: Tuple, output_shape: Tuple):
        """ Set the model for the agent """
        pass

    def set_optimizer(self, optimizer_params: dict): # dict with keys: optimizer, lr, weight_decay
        
        """ Set the optimizer for the model """
        optimizer = optimizer_params["optimizer"]
        optimizer_params_copy = optimizer_params.copy()
        del optimizer_params_copy["optimizer"]

        if optimizer == "Adam":
            self.optimizer = torch.optim.Adam(self.model.parameters(), **optimizer_params_copy)
        elif optimizer == "SGD":
            self.optimizer = torch.optim.SGD(self.model.parameters(), **optimizer_params_copy)
        elif optimizer == "RMSprop":
            self.optimizer = torch.optim.RMSprop(self.model.parameters(), **optimizer_params_copy)
        else:
            raise ValueError(f"Optimizer {optimizer} not supported")

    def draw_action_(self, observation: np.ndarray) -> np.ndarray: #
        
        """ 
        Draw an action based on the fitted model (see predict method)
        """

        # Remove batch dimension if it is one
        if observation.shape[0] == 1:
            observation = observation[0]

        if self.mode=="train":
            action = self.agent.draw_action(observation)
        else:
            action = self.predict(observation) # bypass the agent's draw_action method and directly get prediction from policy network
        
        return action
        
    def predict(self, observation: np.ndarray) -> np.ndarray: #
        """ Do one forward pass of the model directly and return the prediction"""

        if self.mode=="eval":

            # Apply pre-processors of the mushroom agent
            for preprocessor in self.agent.preprocessors:
                observation = preprocessor(observation)
            
            # add batch dimension back to mimic mushroom_rl library
            observation = np.expand_dims(observation, axis=0)
            action = self.predict_(observation)

            return action
        else:
            raise ValueError("Model is in train mode. Use draw_action method instead.")

    def predict_(self, observation: np.ndarray) -> np.ndarray: #
        """ Do one forward pass of the model directly and return the prediction
        Overwrite for agents that have additional steps such as SAC"""

        observation = torch.tensor(observation, dtype=torch.float32).to(self.device)
        action = self.actor.forward(observation)
        action = action.cpu().detach().numpy()

        return action

    def train(self):
        """set the internal state of the agent and its model to train"""
        self.mode = "train"

    def eval(self):
        """set the internal state of the agent and its model to eval"""
        self.mode = "eval"
    

    def to(self, device: str): #
        """Move the model to the specified device"""

        # check if self.model or something else
        self.model.to(device)

    def save(self,
                path: str, # The directory where the file will be saved.
                overwrite: bool=True): # Allow overwriting; if False, a FileExistsError will be raised if the file exists.
        
        """
        Save the PyTorch model to a file in the specified directory.

        """
        
        if not hasattr(self, 'network_list') or self.network_list is None:
            raise AttributeError("Cannot find networks.")

        # Create the directory path if it does not exist
        os.makedirs(path, exist_ok=True)

        # Construct the file path using os.path.join for better cross-platform compatibility

        for network_number, network in enumerate(self.network_list):
            full_path = os.path.join(path, f"network_{network_number}.pth")

            if os.path.exists(full_path):
                if not overwrite:
                    raise FileExistsError(f"The file {full_path} already exists and will not be overwritten.")
                else:
                    logging.debug(f"Overwriting file {full_path}") # Only log with info as during training we will continuously overwrite the model
            
            # Save the model's state_dict using torch.save
            torch.save(network.state_dict(), full_path)
        logging.debug(f"Model saved successfully to {full_path}")

    def load(self, path: str):
        """
        Load the PyTorch models from files in the specified directory.
        """
        
        if not hasattr(self, 'network_list') or self.network_list is None:
            raise AttributeError("Cannot find networks to load.")

        # Check for the presence of model files
        for network_number, network in enumerate(self.network_list):
            full_path = os.path.join(path, f"network_{network_number}.pth")

            if not os.path.exists(full_path):
                raise FileNotFoundError(f"The file {full_path} does not exist.")
            
            try:
                # Load each network's state_dict
                network.load_state_dict(torch.load(full_path))
                logging.info(f"Network {network_number} loaded successfully from {full_path}")
            except Exception as e:
                raise RuntimeError(f"An error occurred while loading network {network_number}: {e}")

    def set_device(self, device: str):

        """ Set the device for the model """

        if device == "cuda":
            if torch.cuda.is_available():
                use_cuda = True
            else:
                logging.warning("CUDA is not available. Using CPU instead.")
                use_cuda = False
        elif device == "cpu":
            use_cuda = False
        else:
            raise ValueError(f"Device {device} not currently not supported, use 'cuda' or 'cpu'")

        return use_cuda

    @staticmethod
    def get_optimizer_class(optimizer_name: str): #

        """ Get optimizer class based on the optimizer name """

        if optimizer_name == "Adam":
            return torch.optim.Adam
        elif optimizer_name == "SGD":
            return torch.optim.SGD
        elif optimizer_name == "RMSprop":
            return torch.optim.RMSprop
        else:
            raise ValueError(f"Optimizer {optimizer_name} not supported")

    @staticmethod
    def get_loss_function(loss: str): #

        """ Get optimizer class based on the optimizer name """

        if loss == "MSE":
            return F.mse_loss
        else:
            raise ValueError(f"Loss {loss} not supported")

    @staticmethod
    def get_input_shape(observation_space: object, flatten_time_dim: bool = True): #

        """ Get the input shape of the model based on the environment info """

        # TODO: Account for more complex spaces like dicts

        observation_space_shape = observation_space.shape

        if flatten_time_dim:
            input_shape = (np.prod(observation_space_shape),)
        else:
            input_shape = observation_space_shape

        return input_shape

    def episode_start(self):

        """ What to do if a new episode starts, e.g., reset policy of the agent
        Often this does not need to do anything (default), otherwise this funciton 
        needs to be overwritten in the subclass. """

        pass

    def fit(self, dataset, **dataset_info):

        """ Hand the fit mehtod to the mushroom agent """

        self.agent.fit(dataset, **dataset_info)

    def stop(self):
        """ Stop the agent """

        self.agent.stop()

    @staticmethod
    # input tuple or list of tuples
    def add_batch_dimension_for_shape(
                        input_shape: Tuple | List[Tuple],
                        batch_dim: int = 1,
                        ) -> Tuple | List[Tuple]:

        """ Add batch dimension to the shape of the input to 
        ensure torchinfo works correctly """

        if isinstance(input_shape, tuple):
            input_shape = (batch_dim,) + input_shape
        elif isinstance(input_shape, list):
            input_shape = [(batch_dim,) + shape for shape in input_shape]
        else:
            raise ValueError("Input shape must be tuple or list of tuples")

        return input_shape
        
