"""Functions to run experiments more efficiently. The usage of these functions is optional and they are only compatible with agents defined in this package. Using agents from other packages such as Stable Baselines or RLlib may require using their own experiment functions."""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/40_experiments/10_experiment_functions.ipynb.

# %% auto 0
__all__ = ['EarlyStoppingHandler', 'calculate_score', 'log_info', 'update_best', 'save_agent', 'test_agent', 'run_test_episode',
           'run_experiment']

# %% ../../nbs/40_experiments/10_experiment_functions.ipynb 3
from abc import ABC, abstractmethod
from typing import Union, List, Tuple, Dict, Literal
import logging
from datetime import datetime  
import numpy as np
import sys
import wandb

from ..envs.base import BaseEnvironment
from ..agents.base import BaseAgent

import importlib

from tqdm import tqdm, trange

# Think about how to handle mushroom integration.
from mushroom_rl.core import Core

# %% ../../nbs/40_experiments/10_experiment_functions.ipynb 4
class EarlyStoppingHandler():

    '''
    Class to handle early stopping during experiments. The EarlyStoppingHandler handler calculates the average
    score over the last "patience" epochs and compares it to the average score over the previous "patience" epochs.
    Note that one epoch we define here as time in between evaluating on a validation set, for supervised learning
    typically one epoch is one pass through the training data. For reinforcement learning, in between each evaluation
    epoch there may be less than one, one, or many episodes played in the training environment.

    '''
    def __init__(
        self,
        patience: int = 50, # Number of epochs to evaluate for stopping
        warmup: int = 100, # How many initial epochs to wait before evaluating
        criteria: str = "J",  # Whether to use discounted rewards J or total rewards R as criteria
        direction: str = "max"  # Whether reward shall be maximized or minimized
    ):

        self.history = list()
        self.patience = patience
        if warmup is None or warmup < patience * 2:
            warmup = patience * 2
        self.warmup = warmup
        self.criteria = criteria
        self.direction = direction

    def add_result(self,
                    J: float, # Return (discounted rewards) of the last epoch
                    R: float, # Total rewards of the last epoch
                    ) -> bool:

        """
        Add the result of the last epoch to the history and check if the experiment should be stopped.

        """
        if self.criteria == "J":
            self.history.append(J)
        elif self.criteria == "R":
            self.history.append(R)
        else:
            raise ValueError("Criteria must be J or R")
        
        if len(self.history) >= self.warmup:
            if self.direction == "max":
                if sum(self.history[-self.patience*2:-self.patience]) >= sum(self.history[-self.patience:]):
                    return True
                else:
                    return False
            elif self.direction == "min":
                if sum(self.history[-self.patience*2:-self.patience]) <= sum(self.history[-self.patience:]):
                    return True
                else:
                    return False
            else:
                raise ValueError("Direction must be max or min")

# %% ../../nbs/40_experiments/10_experiment_functions.ipynb 8
def calculate_score(
                    dataset: List,
                    env: BaseEnvironment, # Any environment inheriting from BaseEnvironment
                    ) -> Tuple[float, float]:

    """

    Calculate the total rewards R and the discounted rewards J of a dataset.

    """

    R = sum([row[0][2] for row in dataset])
    gamma = env.mdp_info.gamma
    J = sum([gamma**(t) * row[0][2] for t, row in enumerate(dataset)]) # Note: t starts at 1 so the first reward is already discounted

    return R, J

def log_info(R: float,
                J: float,
                n_epochs: int,
                tracking: Literal["wandb"], # only wandb implemented so far
                mode: Literal["train", "val", "test"]
                ):
    
    '''
    Logs the same R, J information repeatedly for n_epoochs.
    E.g., to draw a straight line in wandb for algorithmes
    such as XGB, RF, etc. that can be comparared to the learning
    curves of supervised or reinforcement learning algorithms.
    '''

    if tracking == "wandb":
        for epoch in range(n_epochs):
            wandb.log({f"{mode}/R": R, f"{mode}/J": J})
    else:
        pass

def update_best(R: float, J: float, best_R: float, best_J: float): # 
    
    """

    Update the best total rewards R and the best discounted rewards J.

    """

    if R > best_R:
        best_R = R
    if J > best_J:
        best_J = J

    return best_R, best_J

def save_agent(agent: BaseAgent, # Any agent inheriting from BaseAgent
                experiment_dir: str, # Directory to save the agent, 
                save_best: bool,
                R: float,
                J: float,
                best_R: float,
                best_J: float,
                criteria: str = "J",
                force_save = False,
                ):

    """
    Save the agent if it has improved either R or J, depending on the criteria argument,
    vs. the previous epochs

    """

    if save_best:
        if criteria == "R":
            if R == best_R:
                save_dir = f"{experiment_dir}/saved_models/best"
                agent.save(save_dir)
            elif force_save:
                save_dir = f"{experiment_dir}/saved_models/best"
                agent.save(save_dir)
        elif criteria == "J":
            if J == best_J:
                save_dir = f"{experiment_dir}/saved_models/best"
                agent.save(save_dir)
            elif force_save:
                save_dir = f"{experiment_dir}/saved_models/best"
                agent.save(save_dir)

# %% ../../nbs/40_experiments/10_experiment_functions.ipynb 10
def test_agent(agent: BaseAgent,
            env: BaseEnvironment,
            return_dataset = False,
            save_features = False,
            tracking = None, # other: "wandb",
            eval_step_info = False,
):

    """
    Tests the agent on the environment for a single episode
    """
    
    # TODO make it possible to save dataset via tracking tool

    # Run the test episode
    dataset = run_test_episode(env, agent, eval_step_info, save_features = save_features)

    # Calculate the score
    R, J = calculate_score(dataset, env)

    if tracking == "wandb":
        mode = env.mode
        wandb.log({f"{mode}/R": R, f"{mode}/J": J})

    if return_dataset:
        return R, J, dataset
    else:
        return R, J

def run_test_episode(   env: BaseEnvironment, # Any environment inheriting from BaseEnvironment
                        agent: BaseAgent, # Any agent inheriting from BaseAgent
                        eval_step_info: bool = False, # Print step info during evaluation
                        save_features: bool = False, # Save features (observation) of the dataset. Can be turned off since they sometimes become very large with many lag information

                ):

    """
    Runs an episode to test the agent's performance.
    It assumes, that agent and environment are initialized, in test/val mode
    and have done reset.
    """

    # Get initial observation
    obs = env.reset()

    dataset = []
    
    finished = False
    step = 0

    horizon = env.mdp_info.horizon
    
    while not finished:
        
        # Sample action from agent
        action = agent.draw_action(obs)

        # Take a step in the environment

        next_obs, reward, terminated, truncated, info = env.step(action)
        
        logging.debug("##### STEP: %d #####", env.index)
        logging.debug("reward: %s", reward)
        logging.debug("info: %s", info)
        logging.debug("next observation: %s", obs)
        logging.debug("truncated: %s", truncated)

        if save_features:
            sample = (obs, action, reward, next_obs, terminated, truncated) # unlike mushroom do not include policy_state
        else:
            sample = (None, action, reward, None, terminated, truncated)

        obs = next_obs
        
        dataset.append((sample, info))

        finished = terminated or truncated

        if eval_step_info:
            step += 1
            sys.stdout.write(f"\rStep {step}")
            sys.stdout.flush()

    if eval_step_info:
        print()

    return dataset

def run_experiment( agent: BaseAgent,
                    env: BaseEnvironment,

                    n_epochs: int,
                    n_steps: int = None, # Number of steps to interact with the environment per epoch. Will be ignored for direct_fit and epchos_fit agents

                    early_stopping_handler: Union[EarlyStoppingHandler, None] = None,
                    save_best: bool = True,
                    performance_criterion: str = "J", # other: "R"

                    tracking: Union[str, None]  = None, # other: "wandb"

                    results_dir: str = "results",

                    run_id: Union[str, None] = None,

                    print_freq: int = 10,

                    eval_step_info = False,

                    return_score = False,
                ):

    """
    Run an experiment with the given agent and environment for n_epochs. It automaticall dedects if the train mode
    of the agent is direct, epochs_fit or env_interaction and runs the experiment accordingly.

    """

    if return_score:
        R_list = []
        J_list = []

    # use start_time as id if no run_id is given
    if run_id is None:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    experiment_dir = f"{results_dir}/{run_id}"

    print(f"Experiment directory: {experiment_dir}")

    logging.info("Starting experiment")

    env.reset()

    # initial evaluation
    env.val()
    agent.eval()
    R, J = test_agent(agent, env, tracking = tracking)

    env.train()
    agent.train()

    logging.info(f"Initial evaluation: R={R}, J={J}")

    best_J = J 
    best_R = R

    if agent.train_mode == "direct_fit":
        
        logging.info("Starting training with direct fit")
        agent.fit(X=env.dataloader.get_all_X("train"), Y=env.dataloader.get_all_Y("train"))
        logging.info("Finished training with direct fit")

        env.val()
        agent.eval()

        R, J = test_agent(agent, env, tracking = tracking, eval_step_info=eval_step_info)
        best_R, best_J = update_best(R, J, best_R, best_J)

        logging.info(f"Evaluation after training: R={R}, J={J}")

        save_agent(agent, experiment_dir, save_best, R, J, best_R, best_J, performance_criterion, force_save = True) # save even if not best

        log_info(R, J, n_epochs-1, tracking, "val")

        if return_score:
            R_list.append(R)
            J_list.append(J)

    elif agent.train_mode == "epochs_fit":

        # save initial agent
        save_dir = f"{experiment_dir}/saved_models/best"
        agent.save(save_dir)
        
        logging.info("Starting training with epochs fit")
        for epoch in trange(n_epochs):
            
            agent.fit_epoch() # Access to dataloader provided to the agent at initialization

            env.val()
            agent.eval()

            R, J = test_agent(agent, env, tracking = tracking, eval_step_info=eval_step_info)

            if return_score:
                R_list.append(R)
                J_list.append(J)
            
            if ((epoch+1) % print_freq) == 0:
                logging.info(f"Epoch {epoch+1}: R={R}, J={J}")
            
            best_R, best_J = update_best(R, J, best_R, best_J)
            save_agent(agent, experiment_dir, save_best, R, J, best_R, best_J, performance_criterion)
            
            if early_stopping_handler is not None:
                stop = early_stopping_handler.add_result(J, R)
            else:
                stop = False

            if stop:
                log_info(R, J, n_epochs-epoch-1, tracking, "val")
                logging.info(f"Early stopping after {epoch+1} epochs")
                break
        
            env.train()
            agent.train()

        logging.info("Finished training with epochs fit")

    elif agent.train_mode == "env_interaction":

        # save initial agent
        save_dir = f"{experiment_dir}/saved_models/best"
        agent.save(save_dir)

        logging.info("Starting training with env_interaction")

        core = Core(agent, env)

        agent.train()
        env.train()

        if hasattr(agent, "warmup_training_steps"):
            warmup_training = True
            warmup_training_steps = agent.warmup_training_steps
        else:
            warmup_training = False
        
        if hasattr(agent, "n_steps_per_fit"):
            n_steps_per_fit = agent.n_steps_per_fit
        else:
            n_steps_per_fit = 1

        if warmup_training:
            env.set_return_truncation(False) # For mushroom Core to work, the step function should not return the truncation flag
            core.learn(n_steps=warmup_training_steps, n_steps_per_fit=warmup_training_steps, quiet=True)
        
        for epoch in trange(n_epochs):

            env.set_return_truncation(False) # For mushroom Core to work, the step function should not return the truncation flag
            agent.train()
            core.learn(n_steps=n_steps, n_steps_per_fit=n_steps_per_fit, quiet=True)
            env.set_return_truncation(True) # Set back to standard gynmasium behavior

            env.val()
            agent.eval()

            R, J = test_agent(agent, env, tracking = tracking, eval_step_info=eval_step_info)

            if return_score:
                R_list.append(R)
                J_list.append(J)

            if ((epoch+1) % print_freq) == 0:
                logging.info(f"Epoch {epoch+1}: R={R}, J={J}")
            
            best_R, best_J = update_best(R, J, best_R, best_J)
            save_agent(agent, experiment_dir, save_best, R, J, best_R, best_J, performance_criterion)

            if early_stopping_handler is not None:
                stop = early_stopping_handler.add_result(J, R)
            else:
                stop = False

            if stop:
                log_info(R, J, n_epochs-epoch-1, tracking, "val")
                logging.info(f"Early stopping after {epoch+1} epochs")
                break
        
            env.train()
            agent.train()

    else:
        raise ValueError("Unknown train mode")

    if return_score:
        return R_list, J_list

    logging.info(f"Evaluation after training: R={R}, J={J}")
