"""Static inventory environment where a decision only affects the next period (Newsvendor problem)"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../../nbs/20_environments/21_envs_inventory/20_single_period_envs.ipynb.

# %% auto 0
__all__ = ['NewsvendorEnv', 'NewsvendorEnvVariableSL']

# %% ../../../nbs/20_environments/21_envs_inventory/20_single_period_envs.ipynb 3
from abc import ABC, abstractmethod
from typing import Union, Tuple, Literal

from ...utils import Parameter, MDPInfo
from ...dataloaders.base import BaseDataLoader
from ...loss_functions import pinball_loss, quantile_loss
from .base import BaseInventoryEnv

import gymnasium as gym

import numpy as np
import time

# %% ../../../nbs/20_environments/21_envs_inventory/20_single_period_envs.ipynb 4
class NewsvendorEnv(BaseInventoryEnv, ABC):
    
    """
    Class implementing the Newsvendor problem, working for the single- and multi-item case. If underage_cost and overage_cost
    are scalars and there are multiple SKUs, then the same cost is used for all SKUs. If underage_cost and overage_cost are arrays,
    then they must have the same length as the number of SKUs. Num_SKUs can be set as parameter or inferred from the DataLoader.
    """

    def __init__(self,
        underage_cost: Union[np.ndarray, Parameter, int, float] = 1, # underage cost per unit
        overage_cost: Union[np.ndarray, Parameter, int, float] = 1, # overage cost per unit
        q_bound_low: Union[np.ndarray, Parameter, int, float] = 0, # lower bound of the order quantity
        q_bound_high: Union[np.ndarray, Parameter, int, float] = np.inf, # upper bound of the order quantity
        dataloader: BaseDataLoader = None, # dataloader
        num_SKUs: Union[int] = None, # if None it will be inferred from the DataLoader
        gamma: float = 1, # discount factor
        horizon_train: int | str = "use_all_data", # if "use_all_data" then horizon is inferred from the DataLoader
        postprocessors: list[object] | None = None,  # default is empty list
        mode: str = "train", # Initial mode (train, val, test) of the environment
        return_truncation: str = True # whether to return a truncated condition in step function
    ) -> None:

        self.print=False

        num_SKUs = dataloader.num_units if num_SKUs is None else num_SKUs

        if not isinstance(num_SKUs, int):
            raise ValueError("num_SKUs must be an integer.")
        
        self.set_param("num_SKUs", num_SKUs, shape=(1,), new=True)

        self.set_param("q_bound_low", q_bound_low, shape=(num_SKUs,), new=True)
        self.set_param("q_bound_high", q_bound_high, shape=(num_SKUs,), new=True)

        self.set_observation_space(dataloader.X_shape)
        self.set_action_space(dataloader.Y_shape, low = self.q_bound_low, high = self.q_bound_high)
        
        mdp_info = MDPInfo(self.observation_space, self.action_space, gamma=gamma, horizon=horizon_train)
        
        super().__init__(mdp_info=mdp_info,
                            postprocessors = postprocessors, 
                            mode=mode, return_truncation=return_truncation,
                            underage_cost=underage_cost,
                            overage_cost=overage_cost, 
                            dataloader=dataloader,
                            horizon_train = horizon_train)
        
        

    def step_(self, 
            action: np.ndarray # order quantity
            ) -> Tuple[np.ndarray, float, bool, bool, dict]:

        """
        Step function implementing the Newsvendor logic. Note that the dataloader will return an observation and a demand,
        which will be relevant in the next period. The observation will be returned directly, while the demand will be 
        temporarily stored under self.demand and used in the next step.

        """

        # Most agent give by default a batch dimension which is not needed for a single period action.
        # If action shape size is 2 and the first dimensiion is 1, then remove it
        if action.ndim == 2 and action.shape[0] == 1:
            action = np.squeeze(action, axis=0)  # Remove the first dimension

        cost_per_SKU = self.determine_cost(action)
        reward = -np.sum(cost_per_SKU) # negative because we want to minimize the cost

        terminated = False # in this problem there is no termination condition
        
        info = dict(
            demand=self.demand.copy(),
            action=action.copy(),
            cost_per_SKU=cost_per_SKU.copy()
        )

        # Set index will set the index and return True if the index is out of bounds
        truncated = self.set_index()

        if truncated:

            if self.mode == "test" or self.mode == "val":
                observation, self.demand = None, None
            else:
                observation, self.demand = self.get_observation()

            return observation, reward, terminated, truncated, info
        
        else:

            observation, self.demand = self.get_observation()

            if self.print:
                print("next_period:", self.index+1)
                print("next observation:", observation)
                print("next demand:", self.demand)
                time.sleep(3)

            return observation, reward, terminated, truncated, info

    def determine_cost(self, action: np.ndarray) -> np.ndarray:
        """
        Determine the cost per SKU given the action taken. The cost is the sum of underage and overage costs.
        """
        # Compute the cost per SKU
        return pinball_loss(self.demand, action, self.underage_cost, self.overage_cost)

    def update_cu_co(self, cu=None, co=None):
        # Check if the underage_cost and overage_cost are already set
        if not hasattr(self, "underage_cost") or not hasattr(self, "overage_cost"):
            logging.warning("Underage and overage costs were not set previously, setting them as new parameters.")
            self.set_param("underage_cost", cu, shape=(self.num_SKUs[0],), new=True)
            self.set_param("overage_cost", co, shape=(self.num_SKUs[0],), new=True)
        else:
            # If only cu is provided
            if cu is not None and co is None:
                if len(set(self.overage_cost)) == 1:  # Check if overage_cost is consistent across SKUs
                    self.set_param("overage_cost", self.overage_cost[0], shape=(self.num_SKUs[0],))
                else:
                    raise ValueError("Cannot update cu without updating co when co has heterogeneous values across SKUs.")
                self.set_param("underage_cost", cu, shape=(self.num_SKUs[0],))
            
            # If only co is provided
            elif co is not None and cu is None:
                if len(set(self.underage_cost)) == 1:  # Check if underage_cost is consistent across SKUs
                    self.set_param("underage_cost", self.underage_cost[0], shape=(self.num_SKUs[0],))
                else:
                    raise ValueError("Cannot update co without updating cu when cu has heterogeneous values across SKUs.")
                self.set_param("overage_cost", co, shape=(self.num_SKUs[0],))
            
            # If both cu and co are provided
            elif cu is not None and co is not None:
                self.set_param("underage_cost", cu, shape=(self.num_SKUs[0],))
                self.set_param("overage_cost", co, shape=(self.num_SKUs[0],))
            
        # Update the service level if applicable
        if hasattr(self, "sl"):
            sl = self.underage_cost / (self.underage_cost + self.overage_cost)
            self.set_param("sl", sl, shape=(self.num_SKUs[0],))


# %% ../../../nbs/20_environments/21_envs_inventory/20_single_period_envs.ipynb 17
class NewsvendorEnvVariableSL(NewsvendorEnv, ABC):
    def __init__(self,

        # Additional parameters:
        sl_bound_low: Union[np.ndarray, Parameter, int, float] = 0.1, # lower bound of the service level during training
        sl_bound_high: Union[np.ndarray, Parameter, int, float] = 0.9, # upper bound of the service level during training
        sl_distribution: Literal["fixed", "uniform"] = "fixed", # distribution of the random service level during training, if fixed then the service level is fixed to sl_test_val
        evaluation_metric: Literal["pinball_loss", "quantile_loss"] = "quantile_loss", # quantile loss is the generic quantile loss (independent of cost levels) while pinball loss uses the specific under- and overage costs
        sl_test_val: Union[np.ndarray, Parameter, int, float] = None, # service level during test and validation, alternatively use cu and co

        underage_cost: Union[np.ndarray, Parameter, int, float] = 1, # underage cost per unit
        overage_cost: Union[np.ndarray, Parameter, int, float] = 1, # overage cost per unit
        q_bound_low: Union[np.ndarray, Parameter, int, float] = 0, # lower bound of the order quantity
        q_bound_high: Union[np.ndarray, Parameter, int, float] = np.inf, # upper bound of the order quantity
        dataloader: BaseDataLoader = None, # dataloader
        num_SKUs: Union[int] = None, # if None it will be inferred from the DataLoader
        gamma: float = 1, # discount factor
        horizon_train: int | str = "use_all_data", # if "use_all_data" then horizon is inferred from the DataLoader
        postprocessors: list[object] | None = None,  # default is empty list
        mode: str = "train", # Initial mode (train, val, test) of the environment
        return_truncation: str = True, # whether to return a truncated condition in step function
        SKUs_in_batch_dimension: bool = True # whether SKUs in the observation space are in the batch dimension (used for meta-learning)
    
    ) -> None:

        # Determine the number of SKUs
        num_SKUs = dataloader.num_units if num_SKUs is None else num_SKUs

        self.set_param("sl_bound_low", sl_bound_low, shape=(1,), new=True)
        self.set_param("sl_bound_high", sl_bound_high, shape=(1,), new=True)
        self.evaluation_metric = evaluation_metric
        self.check_evaluation_metric
        self.sl_distribution = sl_distribution
        self.check_sl_distribution
        self.SKUs_in_batch_dimension = SKUs_in_batch_dimension

        super().__init__(underage_cost=underage_cost,
                        overage_cost=overage_cost,
                        q_bound_low=q_bound_low,
                        q_bound_high=q_bound_high,
                        dataloader=dataloader,
                        num_SKUs=num_SKUs,
                        gamma=gamma,
                        horizon_train=horizon_train,
                        postprocessors=postprocessors,
                        mode=mode,
                        return_truncation=return_truncation)

        if sl_test_val is not None:
            if self.underage_cost is None and self.overage_cost is None:
                self.set_param("sl", sl_test_val, shape=(num_SKUs[0],), new=True)
            else:
                raise ValueError("sl_test_val can only be used when underage_cost and overage_cost are None.")
        else:
            if self.underage_cost is None or self.overage_cost is None:
                raise ValueError("Either sl_test_val or underage_cost and overage_cost must be provided.")
            sl = self.underage_cost / (self.underage_cost + self.overage_cost)
            self.set_param("sl", sl, shape=(self.num_SKUs[0],), new=True)

    def determine_cost(self, action: np.ndarray) -> np.ndarray: #
        """
        Determine the cost per SKU given the action taken. The cost is the sum of underage and overage costs.
        """

        # Compute the cost per SKU
        if self.mode == "train": # during training only the service level is relevant
            return quantile_loss(self.demand, action, self.sl_period)
        else:
            if self.evaluation_metric == "pinball_loss":
                return pinball_loss(self.demand, action, self.underage_cost, self.overage_cost)
            elif self.evaluation_metric == "quantile_loss":
                return quantile_loss(self.demand, action, self.sl)

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

        spaces = {}
        if isinstance(shape, tuple):
            if samples_dim_included:
                shape = shape[1:] # assumed that the first dimension is the number of samples
            if self.SKUs_in_batch_dimension:
                shape = (self.num_SKUs[0],) + shape
            spaces["features"] = gym.spaces.Box(low=low, high=high, shape=shape, dtype=np.float32)

        elif feature_shape is None:
            pass

        else:
            raise ValueError("Shape for features must be a tuple or None")

        # TODO check if this is a good desig decision
        if self.SKUs_in_batch_dimension:
            spaces["service_level"] = gym.spaces.Box(low=0, high=1, shape=(1,), dtype=np.float32)
        else:
            spaces["service_level"] = gym.spaces.Box(low=0, high=1, shape=(self.num_SKUs[0],), dtype=np.float32)

        self.observation_space = gym.spaces.Dict(spaces)

    @staticmethod # staticmethod such that the dataloader can also use the funciton
    def draw_parameter(distribution, sl_bound_low, sl_bound_high, samples): #
        
        if distribution == "fixed":
            sl = np.random.uniform(sl_bound_low, sl_bound_high, size=(samples,))
        elif distribution == "uniform":
            sl = np.random.uniform(sl_bound_low, sl_bound_high, size=(samples,))
        else:
            raise ValueError("sl_distribution not recognized.")
        
        return sl

    def get_observation(self): #
        
        """
        Return the current observation. This function is for the simple case where the observation
        is only an x,y pair. For more complex observations, this function should be overwritten.
        """

        # print("env mode:", self.mode)
        # print("dataloader mode:", self.dataloader.dataset_type)

        X_item, Y_item = self.dataloader[self.index]

        # check if any value in X_item is nan.

        if np.isnan(X_item).any():
            print("X_item is nan")
            # print index
            print("total index:", self.index)
            print("first nan encountered:", np.argwhere(np.isnan(X_item))[0])
        
        if np.isnan(Y_item).any():
            print("Y_item is nan")
            # print index
            print("total index:", self.index)
            print("first nan encountered:", np.argwhere(np.isnan(Y_item))[0])

        # check if any value in X_item is inf.

        if np.isinf(X_item).any():
            print("X_item is inf")
            # print index
            print("total index:", self.index)
            print("first inf encountered:", np.argwhere(np.isinf(X_item))[0])

            print(X_item)

            raise ValueError("X_item contains inf values.")

        if self.mode == "train":
            sl = self.draw_parameter(self.sl_distribution, self.sl_bound_low, self.sl_bound_high, samples = self.num_SKUs[0])
        else:
            sl = self.sl.copy() # evaluate on fixed sls

        if self.mode != "train":
            if hasattr(self.dataloader, "meta_learn_units") and self.dataloader.meta_learn_units: # dataloaders that train SKU in the batch dimension will put SKU dimension last for validation and test set
                X_item = np.moveaxis(X_item, -1, 0)
 
        self.sl_period = sl # store the service level to assess the action
        
        # print("shape in get observation:", X_item.shape)
        # print("demand in get observation:", Y_item.shape)
        # print("sl in get observation:", sl.shape)

        return {"features": X_item, "service_level": sl}, Y_item

    def check_evaluation_metric(self): #
        if self.evaluation_metric not in ["pinball_loss", "quantile_loss"]:
            raise ValueError("evaluation_metric must be either 'pinball_loss' or 'quantile_loss'.")
        if self.evaluation_metric == "pinball_loss" and (self.underage_cost is None or self.overage_cost is None):
            raise ValueError("Underage and overage costs must be provided for pinball loss.")
        if self.evaluation_metric == "quantile_loss" and (self.sl_test_val is None):
            raise ValueError("sl_test_val must be provided for quantile loss.")
    
    def check_sl_distribution(self): #
        if self.sl_distribution not in ["fixed", "uniform"]:
            raise ValueError("sl_distribution must be 'uniform' or 'fixed'.")

    def set_val_test_sl(self, sl_test_val): #
        self.set_param("sl", sl_test_val, shape=(self.num_SKUs[0],), new=False)
