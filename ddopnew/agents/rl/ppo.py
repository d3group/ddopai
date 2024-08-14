# AUTOGENERATED! DO NOT EDIT! File to edit: ../../../nbs/51_RL_agents/10_PPO_agents.ipynb.

# %% auto 0
__all__ = ['PPOAgent']

# %% ../../../nbs/51_RL_agents/10_PPO_agents.ipynb 4
import logging

# set logging level to INFO
logging.basicConfig(level=logging.INFO)

from abc import ABC, abstractmethod
from typing import Union, Optional, List, Tuple
import numpy as np
import os

from ...envs.base import BaseEnvironment
from .mushroom_rl import MushroomBaseAgent
from ...utils import MDPInfo, Parameter
from ...obsprocessors import FlattenTimeDimNumpy
from ...RL_approximators import MLPState, MLPActor
from ...postprocessors import ClipAction

from ...dataloaders.base import BaseDataLoader

from mushroom_rl.algorithms.actor_critic.deep_actor_critic import PPO
from mushroom_rl.policy import GaussianTorchPolicy

import torch
import torch.optim as optim
import torch.nn.functional as F
from torchinfo import summary

import time

# %% ../../../nbs/51_RL_agents/10_PPO_agents.ipynb 5
class PPOAgent(MushroomBaseAgent):

    """
    XXX
    """

    # TODO: Make structure same to SAC with TD3 base class

    def __init__(self, 
                environment_info: MDPInfo,

                learning_rate_actor: float = 3e-4,
                learning_rate_critic: float | None = None, # If none, then it is set to learning_rate_actor
                batch_size: int = 64,
                hidden_layers: List = None, # if None, then default is [64, 64]
                activation: str = "relu", # "relu", "sigmoid", "tanh", "leakyrelu", "elu"
                # tau: float = 0.005,
                std_0: float = 0.1,
                n_epochs_policy: int = 4,
                eps_ppo: float = 0.2,
                lam: float = 0.95,
                ent_coeff: float = 0.,
                n_steps_per_fit=1000,

                drop_prob: float = 0.0,
                batch_norm: bool = False,
                init_method: str = "xavier_uniform", # "xavier_uniform", "xavier_normal", "he_normal", "he_uniform", "normal", "uniform"

                optimizer: str = "Adam", # "Adam" or "SGD" or "RMSprop"  
                loss: str = "MSE", # currently only MSE is supported     
                obsprocessors: list | None = None,      # default: []
                device: str = "cpu", # "cuda" or "cpu"
                agent_name: str | None = "SAC",
                ):

        self.n_steps_per_fit=n_steps_per_fit

        # The standard TD3 agent needs a 2D input, so we need to flatten the time dimension
        flatten_time_dim_processor = FlattenTimeDimNumpy(allow_2d=True, batch_dim_included=False)
        obsprocessors = (obsprocessors or []) + [flatten_time_dim_processor]

        use_cuda = self.set_device(device)

        hidden_layers = hidden_layers or [64, 64]

        OptimizerClass=self.get_optimizer_class(optimizer)
        learning_rate_critic = learning_rate_critic or learning_rate_actor
        lossfunction = self.get_loss_function(loss)

        input_shape = self.get_input_shape(environment_info.observation_space)
        actor_output_shape = environment_info.action_space.shape

        policy_params = dict(network=MLPActor,

                                input_shape=input_shape,
                                output_shape=actor_output_shape,

                                hidden_layers=hidden_layers,
                                activation=activation,
                                drop_prob=drop_prob,
                                batch_norm=batch_norm,
                                init_method=init_method,

                                use_cuda=use_cuda,
                                dropout=self.dropout,

                                st_0=std_0,

                                )
                            
        policy = GaussianTorchPolicy(**policy_params)

        actor_optimizer = {'class': OptimizerClass,
            'params': {'lr': learning_rate_actor}} 

        critic_params = dict(network=MLPState,
                optimizer={'class': OptimizerClass,
                        'params': {'lr': learning_rate_critic}}, 
                loss=lossfunction,
                input_shape=input_shape,
                output_shape=(1,),

                hidden_layers=hidden_layers,
                activation=activation,
                drop_prob=drop_prob,
                batch_norm=batch_norm,
                init_method=init_method,

                use_cuda=use_cuda,
                dropout=self.dropout,)

        self.agent = PPO(
            mdp_info=environment_info,
            policy=policy,
            actor_optimizer=actor_optimizer,
            critic_params=critic_params,
            n_epochs_policy=n_epochs_policy,
            batch_size=batch_size,
            eps_ppo=eps_ppo,
            lam=lam,
            ent_coeff=ent_coeff,
            critic_fit_params=None
        )

        super().__init__(
            environment_info=environment_info,
            obsprocessors=obsprocessors,
            device=device,
            agent_name=agent_name
        )

        logging.info("Actor network:")
        if logging.getLogger().isEnabledFor(logging.INFO):
            input_size = self.add_batch_dimension_for_shape(input_shape)
            print(summary(self.actor, input_size=input_size))
            time.sleep(.2)

        logging.info("Critic network:")
        if logging.getLogger().isEnabledFor(logging.INFO):
            input_size = self.add_batch_dimension_for_shape(input_shape)
            print(summary(self.critic, input_size=input_size))

    def get_network_list(self, set_actor_critic_attributes: bool = True):
        """ Get the list of networks in the agent for the save and load functions
        Get the actor for the predict function in eval mode """

        critic = self.agent._V._impl.model.network
        actor = self.agent.policy._mu._impl.model.network

        networks = []
        networks.append(critic)
        networks.append(actor)

        if set_actor_critic_attributes:
            return networks, actor, critic
        else:
            return networks
