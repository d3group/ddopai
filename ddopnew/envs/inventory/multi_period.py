# AUTOGENERATED! DO NOT EDIT! File to edit: ../../../nbs/21_envs_inventory/30_multi_period_envs.ipynb.

# %% auto 0
__all__ = ['MultiPeriodEnv']

# %% ../../../nbs/21_envs_inventory/30_multi_period_envs.ipynb 3
from abc import ABC, abstractmethod
from typing import Union, Tuple

from ...utils import Parameter, MDPInfo, check_parameter_types
from ...dataloaders.base import BaseDataLoader
from .base import BaseInventoryEnv
from .inventory_utils import OrderPipeline

import gymnasium as gym

import numpy as np
import time

# %% ../../../nbs/21_envs_inventory/30_multi_period_envs.ipynb 4
class MultiPeriodEnv(BaseInventoryEnv, ABC):
    
    """
    XXX.
    """

    def __init__(self,
        
        underage_cost: np.ndarray | Parameter | int | float = 1,  # underage cost per unit
        overage_cost: np.ndarray | Parameter | int | float = 0,  # overage cost per unit (zero in most cases)

        fixed_ordering_cost: np.ndarray | Parameter | int | float = 0,  # fixed ordering cost (applies per SKU, not jointly)
        variable_ordering_cost: np.ndarray | Parameter | int | float = 0,  # variable ordering cost per unit
        holding_cost: np.ndarray | Parameter | int | float = 1,  # holding cost per unit

        start_inventory: np.ndarray | Parameter | int | float = 0,  # initial inventory
        max_inventory: np.ndarray | Parameter | int | float = np.inf,  # maximum inventory

        inventory_pipeline_params: dict | None = None,  # parameters for the inventory pipeline, only lead_time_mean must be given. 

        q_bound_low: np.ndarray | Parameter | int | float = 0,  # lower bound of the order quantity
        q_bound_high: np.ndarray | Parameter | int | float = np.inf,  # upper bound of the order quantity
        dataloader: BaseDataLoader = None,  # dataloader
        num_SKUs: int | None = None,  # if None, it will be inferred from the DataLoader
        gamma: float = 1,  # discount factor
        horizon_train: int | str = 100,  # if "use_all_data", then horizon is inferred from the DataLoader
        postprocessors: list[object] | None = None,  # default is an empty list
        mode: str = "train",  # Initial mode (train, val, test) of the environment
        return_truncation: bool = True,  # whether to return a truncated condition in step function
        step_info_verbosity = 0,  # 0: no info, 1: some info, 2: all info

    ) -> None:

        self.print=False

        num_SKUs = dataloader.num_units if num_SKUs is None else num_SKUs
        if not isinstance(num_SKUs, int):
            raise ValueError("num_SKUs must be an integer.")
        
        self.set_param("num_SKUs", num_SKUs, new=True)

        self.set_param("q_bound_low", q_bound_low, shape=(num_SKUs,), new=True)
        self.set_param("q_bound_high", q_bound_high, shape=(num_SKUs,), new=True)

        self.set_param("fixed_ordering_cost", fixed_ordering_cost, shape=(num_SKUs,), new=True)
        self.set_param("variable_ordering_cost", variable_ordering_cost, shape=(num_SKUs,), new=True)
        self.set_param("holding_cost", holding_cost, shape=(num_SKUs,), new=True)

        self.set_param("start_inventory", start_inventory, shape=(num_SKUs,), new=True)
        self.set_param("max_inventory", max_inventory, shape=(num_SKUs,), new=True)
        self.start_inventory = self.start_inventory.astype(float)

        inventory_pipeline_params = inventory_pipeline_params or {}
        inventory_pipeline_params["num_units"] = int(self.num_SKUs[0])
        self.order_pipeline = OrderPipeline(**inventory_pipeline_params)
        self.inventory = self.start_inventory.copy()

        self.set_observation_space(dataloader.X_shape)
        self.set_action_space(dataloader.Y_shape, low = self.q_bound_low, high = self.q_bound_high)

        mdp_info = MDPInfo(self.observation_space, self.action_space, gamma=gamma, horizon=horizon_train)

        check_parameter_types(step_info_verbosity, parameter_type=int)
        self.step_info_verbosity = step_info_verbosity
        
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
        XXX.

        """

        # Most agent give by default a batch dimension which is not needed for a single period action.
        # If action shape size is 2 and the first dimensiion is 1, then remove it
        if action.ndim == 2 and action.shape[0] == 1:
            action = np.squeeze(action, axis=0)  # Remove the first dimension

        variable_ordering_cost = action * self.variable_ordering_cost
        fixed_ordering_cost = np.where(action > 0, self.fixed_ordering_cost, 0)

        orders_arriving = self.order_pipeline.step(action) # add orders to pipeline and get arriving orders

        # print("action:", action)
        # print("unit cost:", self.variable_ordering_cost)
        # print("variable_ordering_cost:", variable_ordering_cost)

        # print("unit_fixed_ordering_cost:", self.fixed_ordering_cost)
        # print("fixed_ordering_cost:", fixed_ordering_cost)

        # print("old inventory:", self.inventory)
        # print("orders arriving:", orders_arriving)
        # print("demand:", self.demand)

        self.inventory += orders_arriving
        self.inventory -= self.demand
        self.inventory = np.minimum(self.inventory, self.max_inventory)

        

        # check where the inventory is below 0
        underage_quantity = np.maximum(-self.inventory, 0)
        underage_cost = underage_quantity * self.underage_cost
        # print("underage_quantity:", underage_quantity, "underage_cost:", underage_cost)
        self.inventory = np.maximum(self.inventory, 0)

        holding_cost = self.inventory * self.holding_cost
        # print("holding_cost:", holding_cost)
        # print("new inventory:", self.inventory)

        total_cost_step = variable_ordering_cost + fixed_ordering_cost + underage_cost + holding_cost
        reward = -np.sum(total_cost_step) # negative because we want to minimize the cost

        terminated = False # in this problem there is no termination condition
        
        info = {}
        if self.step_info_verbosity > 1:
            info["demand"] = self.demand.copy()
            info["action"] = action.copy()
            info["cost_per_SKU"] = total_cost_step.copy()
        if self.step_info_verbosity > 0:
            info["variable_ordering_cost"] = variable_ordering_cost.copy()
            info["fixed_ordering_cost"] = fixed_ordering_cost.copy()
            info["underage_cost"] = underage_cost.copy()
            info["holding_cost"] = holding_cost.copy()

        # Set index will set the index and return True if the index is out of bounds
        truncated = self.set_index()

        if truncated:

            observation = self.observation_space.sample()
            for key, value in observation.items():
                observation[key] = np.zeros_like(value)
            demand = np.zeros_like(self.action_space.sample())

            return observation, reward, terminated, truncated, info
        
        else:

            observation, self.demand = self.get_observation()

            if self.print:
                print("next_period:", self.index+1)
                print("next observation:", observation)
                print("next demand:", self.demand)
                time.sleep(3)

            return observation, reward, terminated, truncated, info
        
    def get_observation(self):
        
        """
        Return the current observation. This function is for the simple case where the observation
        is only an x,y pair. For more complex observations, this function should be overwritten.

        """

        
        X_item, Y_item = self.dataloader[self.index]

        observation = {
            "features": X_item,
            "order_pipeline": self.order_pipeline.get_pipeline(),
            "inventory:": self.inventory,
        }

        return observation, Y_item


    def reset(self,
        start_index: int | str = None, # index to start from
        state: np.ndarray = None # initial state
        ) -> Tuple[np.ndarray, bool]:

        """
        Reset function for the Newsvendor problem. It will return the first observation and demand.
        For val and test modes, it will by default reset to 0, while for the train mode it depends
        on the paramter "horizon_train" whether a random point in the training data is selected or 0
        """

        self.order_pipeline.reset()
        self.inventory = self.start_inventory.copy()

        truncated = self.reset_index(start_index)

        observation, self.demand = self.get_observation()

        # print("in reset:", observation)
        
        return observation

    def set_observation_space(self,
                            feature_shape: tuple, # shape of the dataloader features
                            feature_low: Union[np.ndarray, float] = -np.inf, # lower bound of the observation space
                            feature_high: Union[np.ndarray, float] = np.inf, # upper bound of the observation space
                            samples_dim_included = True # whether the first dimension of the shape input is the number of samples
                            ) -> None:
        
        '''
        Set the observation space of the environment.

        '''

        # To handle cases when no external information is available (e.g., parametric NV)

        spaces = {}

        if isinstance(feature_shape, tuple):
            if samples_dim_included:
                feature_shape = feature_shape[1:] # assumed that the first dimension is the number of samples
            spaces["features"] = gym.spaces.Box(low=feature_low, high=feature_high, shape=feature_shape, dtype=np.float32)
        elif feature_shape is None:
            pass
        else:
            raise ValueError("Shape for features must be a tuple or None")

        len_pipeline, num_products = self.order_pipeline.shape
        order_pipeline_shape = self.order_pipeline.shape
        
        # add dim with lengh of order pipeline and copy values in that dimension

        q_bound_low_full = np.tile(self.q_bound_low, (len_pipeline, 1))
        q_bound_high_full = np.tile(self.q_bound_high, (len_pipeline, 1))
        
        spaces["order_pipeline"] = gym.spaces.Box(low=q_bound_low_full, high=q_bound_high_full, shape=order_pipeline_shape, dtype=np.float32)
        spaces["inventory"] = gym.spaces.Box(low=0, high=self.max_inventory, shape=(int(self.num_SKUs[0]),), dtype=np.float32)
        
        self.observation_space = gym.spaces.Dict(spaces)