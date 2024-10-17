"""Newsvendor agents based on Empirical Risk Minimization (ERM) principles."""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../../nbs/30_agents/41_NV_agents/11_NV_erm_agents.ipynb.

# %% auto 0
__all__ = ['NewsvendorXGBAgent', 'SGDBaseAgent', 'NVBaseAgent', 'NewsvendorlERMAgent', 'NewsvendorDLAgent', 'BaseMetaAgent',
           'NewsvendorlERMMetaAgent', 'NewsvendorDLMetaAgent', 'NewsvendorDLTransformerAgent',
           'NewsvendorDLTransformerMetaAgent']

# %% ../../../nbs/30_agents/41_NV_agents/11_NV_erm_agents.ipynb 3
import logging

from abc import ABC, abstractmethod
from typing import Union, Optional, List, Tuple, Literal, Callable, Dict
import numpy as np
import os
from tqdm import tqdm
import time
from IPython import get_ipython

import xgboost as xgb

from ...envs.base import BaseEnvironment
from ..base import BaseAgent
from ...utils import MDPInfo, Parameter, DatasetWrapper, DatasetWrapperMeta
from ...torch_utils.loss_functions import TorchQuantileLoss, TorchPinballLoss
from ..obsprocessors import FlattenTimeDimNumpy
from ...dataloaders.base import BaseDataLoader
from ..ml_utils import LRSchedulerPerStep

import torch

from torchinfo import summary

# %% ../../../nbs/30_agents/41_NV_agents/11_NV_erm_agents.ipynb 4
class NewsvendorXGBAgent(BaseAgent):

    """
    Agent solving the Newsvendor problem within the ERM framework (i.e., using quantile regression)
    using the XGBoost library.
    """

    def __init__(self,

                    environment_info: MDPInfo,
                    cu: float | np.ndarray, # underage cost
                    co: float | np.ndarray, # overage cost
                    obsprocessors: Optional[List[object]] = None,
                    agent_name: str | None = "XGBAgent",

                    ### XGB params
                    eta: float = 0.3,
                    gamma: float = 0,
                    max_depth: int = 6,
                    min_child_weight: float = 1,
                    max_delta_step: float = 0,
                    subsample: float = 1,
                    sampling_method: str = "uniform",
                    colsample_bytree: float = 1,
                    colsample_bylevel: float = 1,
                    colsample_bynode: float = 1,
                    lambda_: float = 1,
                    alpha: float = 0,
                    tree_method: str = "auto",
                    scale_pos_weight: float = 1,
                    # updater will always use default
                    refresh_leaf: int = 1,
                    # process type will always use default
                    grow_policy: str = "depthwise",
                    max_leaves: int = 0,
                    max_bin: int = 256,
                    num_parallel_tree: int = 1,
                    multi_strategy: str = "one_output_per_tree",
                    max_cached_hist_node: int = 65536,

                    ### General params
                    nthread: int = 1,
                    device: str = "CPU"):

        # if float, convert to array
        cu = self.convert_to_numpy_array(cu)
        co = self.convert_to_numpy_array(co)

        self.sl = cu / (cu + co)
        self.fitted = False

        self.model = xgb.XGBRegressor(
            objective = "reg:quantileerror",
            quantile_alpha = self.sl[0],

            eta=eta,
            gamma=gamma,
            max_depth=max_depth,
            min_child_weight=min_child_weight,
            max_delta_step=max_delta_step,
            subsample=subsample,
            sampling_method=sampling_method,
            colsample_bytree=colsample_bytree,
            colsample_bylevel=colsample_bylevel,
            colsample_bynode=colsample_bynode,
            lambda_=lambda_,
            alpha=alpha,
            tree_method=tree_method,
            scale_pos_weight=scale_pos_weight,
            # updater will always use default
            refresh_leaf=refresh_leaf,
            # process type will always use default
            grow_policy=grow_policy,
            max_leaves=max_leaves,
            max_bin=max_bin,
            num_parallel_tree=num_parallel_tree,
            multi_strategy=multi_strategy,
            max_cached_hist_node=max_cached_hist_node,
            nthread=nthread,
            device=device
        )
        
        super().__init__(environment_info = environment_info, obsprocessors = obsprocessors, agent_name = agent_name)

        # TODO: For consistency, this needs to be done outside the package when defining the experiment.
        # # check if FlattenTimeDimNumpy in obsprocessors
        # if not any(isinstance(p, FlattenTimeDimNumpy) for p in self.obsprocessors):
        #     self.add_obsprocessor(FlattenTimeDimNumpy(allow_2d=True))

    def fit(self,
            X: np.ndarray, # features will be ignored
            Y: np.ndarray) -> None:

        """

        Fit the agent to the data by training the XGBoost model.

        """

        if X.ndim == 3:
            X = X.reshape(X.shape[0], -1)
        self.model.fit(X, Y)
        self.fitted = True
    
    def draw_action_(self, 
                    observation: np.ndarray) -> np.ndarray: #
        """

        Draw an action from the model given an observation.
        
        """


        if self.fitted == False:
            return np.array([0.0])

        return self.model.predict(observation)

    
    def save(self,
            path: str,  # The directory where the file will be saved.
            overwrite: bool=True):  # Allow overwriting; if False, a FileExistsError will be raised if the file exists.

        """
        Save the XGBoost model to a file in the specified directory.
        """

        if not hasattr(self, 'fitted') or not self.fitted:
            raise ValueError("Agent has not been fitted yet. Train the model before saving.")
        
        if not hasattr(self, 'model') or self.model is None:
            raise ValueError("Agent has no model to save. The model might not have been trained or initialized.")

        os.makedirs(path, exist_ok=True)

        full_path = os.path.join(path, "xgb_model.json")  # XGBoost models can be saved as .json or .model

        if os.path.exists(full_path):
            if not overwrite:
                raise FileExistsError(f"The file {full_path} already exists and will not be overwritten.")
            else:
                logging.warning(f"Overwriting file {full_path}")

        self.model.save_model(full_path)

    def load(self, path: str):
        full_path = os.path.join(path, "xgb_model.json")
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"The file {full_path} does not exist.")
        
        try:
            self.model = xgb.XGBRegressor()  # Use XGBRegressor instead of Booster
            self.model.load_model(full_path)
            self.fitted = True
            logging.info(f"Model loaded successfully from {full_path}")
        except Exception as e:
            raise ValueError(f"An error occurred while loading the model: {e}")



# %% ../../../nbs/30_agents/41_NV_agents/11_NV_erm_agents.ipynb 5
class SGDBaseAgent(BaseAgent):

    """
    Base class for Agents that are trained using Stochastic Gradient Descent (SGD) on PyTorch models.
    """

    # TODO: Remove input shapes as input end get from MDPInfo

    train_mode = "epochs_fit"
    
    def __init__(self, 
            environment_info: MDPInfo,
            dataloader: BaseDataLoader,
            input_shape: Tuple,
            output_shape: Tuple,
            dataset_params: Optional[dict] = None, # parameters needed to convert the dataloader to a torch dataset
            dataloader_params: Optional[dict] = None, # default: {"batch_size": 32, "shuffle": True}
            optimizer_params: Optional[dict] = None,  # default: {"optimizer": "Adam", "lr": 0.01, "weight_decay": 0.0}
            learning_rate_scheduler_params: Dict | None = None, # default: None. If dict, then first key is "scheduler" and the rest are the parameters
            obsprocessors: Optional[List] = None,     # default: []
            device: str = "cpu", # "cuda" or "cpu"
            agent_name: str | None = None,
            test_batch_size: int = 1024,
            receive_batch_dim: bool = False,
            ):
        
        # Initialize default values for mutable arguments
        optimizer_params = optimizer_params or {"optimizer": "Adam", "lr": 0.01, "weight_decay": 0.0}
        dataloader_params = dataloader_params or {"batch_size": 32, "shuffle": True}
        dataset_params = dataset_params or {}

        self.device = self.set_device(device)
        
        self.set_dataloader(dataloader, dataset_params, dataloader_params)

        self.set_model(input_shape, output_shape)
        self.loss_function_params=None # default
        self.set_loss_function()
        self.set_optimizer(optimizer_params)
        self.set_learning_rate_scheduler(learning_rate_scheduler_params)
        self.test_batch_size = test_batch_size

        super().__init__(environment_info = environment_info, obsprocessors = obsprocessors, agent_name = agent_name, receive_batch_dim = receive_batch_dim)

        batch_dim = 1
        logging.info("Network architecture:")
        if logging.getLogger().isEnabledFor(logging.INFO):

            self.model.eval()
            print(self.obsprocessors)
            if any(isinstance(obsprocessor, FlattenTimeDimNumpy) for obsprocessor in self.obsprocessors):
                input_size = (batch_dim, int(np.prod(input_shape)))
            else:
                input_size = (batch_dim, *input_shape)

            input_tensor = torch.randn(*input_size).to(self.device)
            input_tuple = (input_tensor,)

            if get_ipython() is not None:
                print(summary(self.model, input_data=input_tuple, device=self.device))
            else:
                summary(self.model, input_data=input_tuple, device=self.device)
            time.sleep(0.2)

        self.to(self.device)

    def set_device(self, device: str):

        """ Set the device for the model """

        if device == "cuda":
            if torch.cuda.is_available():
                return "cuda"
            else:
                logging.warning("CUDA is not available. Using CPU instead.")
                return "cpu"
        elif device == "cpu":
            return "cpu"
        else:
            raise ValueError(f"Device {device} not currently not supported, use 'cuda' or 'cpu'")


    def set_dataloader(self,
                        dataloader: BaseDataLoader,
                        dataset_params: dict,
                        dataloader_params: dict, # dict with keys: batch_size, shuffle
                        ) -> None: 

        """
        Set the dataloader for the agent by wrapping it into a Torch Dataset
        
        """

        # check if class already have a dataloader
        if not hasattr(self, 'dataloader'):

            dataset = DatasetWrapper(dataloader, **dataset_params)
            self.dataloader = torch.utils.data.DataLoader(dataset, **dataloader_params)

    @abstractmethod
    def set_loss_function(self):
        """ Set loss function for the model """
        pass

    @abstractmethod
    def set_model(self, input_shape: Tuple, output_shape: Tuple):
        """ Set the model for the agent """
        pass

    def set_optimizer(self, optimizer_params: dict): # dict with keys: optimizer, lr, weight_decay
        
        """ Set the optimizer for the model """

        if not hasattr(self, 'optimizer'):
            
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
        
    def set_learning_rate_scheduler(self, learning_rate_scheduler_params): #
        """ Set learning rate scheudler (can be None) """

        if learning_rate_scheduler_params is not None:

            params = learning_rate_scheduler_params.copy()
            scheduler_type = params["scheduler"]
            del params["scheduler"]
            if scheduler_type == "LRSchedulerPerStep":
                self.learning_rate_scheduler = LRSchedulerPerStep(self.optimizer, **params)
            else:
                raise ValueError(f"Learning rate scheduler {scheduler_type} not supported")

        else:
            self.learning_rate_scheduler = None

    def fit_epoch(self):

        """ Fit the model for one epoch using the dataloader """

        device = next(self.model.parameters()).device
        self.model.train()
        total_loss=0

        for i, output in enumerate(tqdm(self.dataloader)):
            
            if len(output)==3:
                X, y, loss_function_params = output
            else:
                X, y = output
                loss_function_params = None

            # convert X and y to float32
            X = X.type(torch.float32)
            y = y.type(torch.float32)
            
            X, y = X.to(device), y.to(device)

            self.optimizer.zero_grad()

            y_pred = self.model(X)

            if loss_function_params is not None:
                loss = self.loss_function(y_pred, y, **loss_function_params)
            elif self.loss_function_params is not None:
                loss = self.loss_function(y_pred, y, **self.loss_function_params)
            else:
                loss = self.loss_function(y_pred, y)

            loss.backward()
            self.optimizer.step()

            if self.learning_rate_scheduler is not None:
                self.learning_rate_scheduler.step()
        
            total_loss += loss.item()
        
        self.model.eval()
        
        return total_loss

    def draw_action_(self, observation: np.ndarray) -> np.ndarray: #
        
        """ 
        Draw an action based on the fitted model (see predict method)
        """
        
        action = self.predict(observation)
        
        return action
    
    @staticmethod
    def split_into_batches(X: np.ndarray, batch_size: int) -> List[np.ndarray]: #
        """ Split the input into batches of the specified size """
        return [X[i:i+batch_size] for i in range(0, len(X), batch_size)]

    def predict(self, X: np.ndarray) -> np.ndarray: #
        """ Do one forward pass of the model and return the prediction """

        device = next(self.model.parameters()).device
        self.model.eval()

        batches = self.split_into_batches(X, self.test_batch_size)

        y_pred_full = []
        for batch in batches:

            X = batch

            X = torch.tensor(X, dtype=torch.float32)
            X = X.to(device)

            with torch.no_grad():

                y_pred = self.model(X)

                # check if y_pred is not finite:
                if not torch.all(torch.isfinite(y_pred)):

                    print(y_pred)

                    # check if X is not finite:
                    if not torch.all(torch.isfinite(X)):

                        print("X is not finite")
                        print("total X_shape: ", X.shape)
                        print("non-finite indices: ", torch.nonzero(~torch.isfinite(X)))
                        print(X)


                    raise ValueError("Predicted values are not finite")

            y_pred = y_pred.cpu().numpy()

            y_pred_full.append(y_pred)
        
        y_pred_full = np.concatenate(y_pred_full, axis=0)

        return y_pred_full

    def train(self):
        """set the internal state of the agent and its model to train"""
        self.mode = "train"
        self.model.train()

    def eval(self):
        """set the internal state of the agent and its model to eval"""
        self.mode = "eval"
        self.model.eval()

    def to(self, device: str): #
        """Move the model to the specified device"""
        self.model.to(device)

    def save(self,
                path: str, # The directory where the file will be saved.
                overwrite: bool=True): # Allow overwriting; if False, a FileExistsError will be raised if the file exists.
        
        """
        Save the PyTorch model to a file in the specified directory.

        """
        
        if not hasattr(self, 'model') or self.model is None:
            raise AttributeError("Model is not defined in the class.")

        # Create the directory path if it does not exist
        os.makedirs(path, exist_ok=True)

        # Construct the file path using os.path.join for better cross-platform compatibility
        full_path = os.path.join(path, "model.pth")

        if os.path.exists(full_path):
            if not overwrite:
                raise FileExistsError(f"The file {full_path} already exists and will not be overwritten.")
            else:
                logging.debug(f"Overwriting file {full_path}") # Only log with info as during training we will continuously overwrite the model
        
        # Save the model's state_dict using torch.save
        torch.save(self.model.state_dict(), full_path)
        logging.debug(f"Model saved successfully to {full_path}")

    def load(self, path: str): # Only the path to the folder is needed, not the file itself
 
        """
        Load the PyTorch model from a file.
        """
        
        if not hasattr(self, 'model') or self.model is None:
            raise AttributeError("Model is not defined in the class.")

        # Construct the file path
        full_path = os.path.join(path, "model.pth")

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"The file {full_path} does not exist.")

        try:
            # Load the model's state_dict using torch.load
            if self.device == "cuda":
                self.model.load_state_dict(torch.load(full_path))
            else:
                self.model.load_state_dict(torch.load(full_path, map_location=torch.device('cpu')))
            logging.debug(f"Model loaded successfully from {full_path}")
        except Exception as e:
            raise RuntimeError(f"An error occurred while loading the model: {e}")
    

# %% ../../../nbs/30_agents/41_NV_agents/11_NV_erm_agents.ipynb 21
class NVBaseAgent(SGDBaseAgent):

    """
    Base agent for the Newsvendor problem implementing
    the loss function for the Empirical Risk Minimization (ERM) approach
    based on quantile loss.
    """

    def __init__(self, 
                environment_info: MDPInfo,
                dataloader: BaseDataLoader,
                cu: np.ndarray | Parameter,
                co: np.ndarray | Parameter,
                input_shape: Tuple,
                output_shape: Tuple,
                optimizer_params: dict | None = None,  # default: {"optimizer": "Adam", "lr": 0.01, "weight_decay": 0.0}
                learning_rate_scheduler_params = None,  # TODO: add base class for learning rate scheduler for typing
                dataset_params: dict | None = None, # parameters needed to convert the dataloader to a torch dataset
                dataloader_params: dict | None = None,  # default: {"batch_size": 32, "shuffle": True}
                obsprocessors: list | None = None,      # default: []
                device: str = "cpu", # "cuda" or "cpu"
                agent_name: str | None = None,
                test_batch_size: int = 1024,
                receive_batch_dim: bool = False,
                loss_function: Literal["quantile", "pinball"] = "quantile", 
                ):

        cu = self.convert_to_numpy_array(cu)
        co = self.convert_to_numpy_array(co)
        
        self.sl = cu / (cu + co) # ensure this works if cu and co are Parameters
        self.cu = cu
        self.co = co

        self.loss_function = loss_function


        super().__init__(
            environment_info=environment_info,
            dataloader=dataloader,
            input_shape=input_shape,
            output_shape=output_shape,
            optimizer_params=optimizer_params,
            learning_rate_scheduler_params=learning_rate_scheduler_params,
            dataset_params=dataset_params,
            dataloader_params=dataloader_params,
            obsprocessors=obsprocessors,
            device=device,
            agent_name=agent_name,
            test_batch_size=test_batch_size,
            receive_batch_dim=receive_batch_dim,
        )   
        
    def set_loss_function(self):
        
        """Set the loss function for the model to the quantile loss. For training
        the model uses quantile loss and not the pinball loss with specific cu and 
        co values to ensure similar scale of the feedback signal during training."""

        if self.loss_function == "quantile":
            self.loss_function_params = {"quantile": self.sl}
            self.loss_function = TorchQuantileLoss(reduction="mean")
            logging.debug(f"Loss function set to {self.loss_function}")

        elif self.loss_function == "pinball":
            self.loss_function_params = {"underage": self.cu, "overage": self.co}
            self.loss_function = TorchPinballLoss(reduction="mean")
            logging.debug(f"Loss function set to {self.loss_function}")

        else:
            raise ValueError(f"Loss function {self.loss_function} not supported")

# %% ../../../nbs/30_agents/41_NV_agents/11_NV_erm_agents.ipynb 24
class NewsvendorlERMAgent(NVBaseAgent):

    """
    Newsvendor agent implementing Empirical Risk Minimization (ERM) approach 
    based on a linear (regression) model. Note that this implementation finds
    the optimal regression parameters via SGD.

    """

    def __init__(self, 
                environment_info: MDPInfo,
                dataloader: BaseDataLoader,
                cu: np.ndarray | Parameter,
                co: np.ndarray | Parameter,
                input_shape: Tuple,
                output_shape: Tuple,
                optimizer_params: dict | None = None,  # default: {"optimizer": "Adam", "lr": 0.01, "weight_decay": 0.0}
                learning_rate_scheduler_params = None,  # TODO: add base class for learning rate scheduler for typing
                model_params: dict | None = None,  # default: {"relu_output": False}
                dataset_params: dict | None = None, # parameters needed to convert the dataloader to a torch dataset
                dataloader_params: dict | None = None,  # default: {"batch_size": 32, "shuffle": True}
                obsprocessors: list | None = None,  # default: []
                device: str = "cpu",  # "cuda" or "cpu"
                agent_name: str | None = "lERM",
                test_batch_size: int = 1024,
                receive_batch_dim: bool = False,
                loss_function: Literal["quantile", "pinball"] = "quantile", 
                ):

        # Handle mutable defaults unique to this class
        default_model_params = {
            "relu_output": False
            }

        self.model_params = self.update_model_params(default_model_params, model_params or {})

        super().__init__(
            environment_info=environment_info,
            dataloader=dataloader,
            cu=cu,
            co=co,
            input_shape=input_shape,
            output_shape=output_shape,
            optimizer_params=optimizer_params,
            learning_rate_scheduler_params=learning_rate_scheduler_params,
            dataloader_params=dataloader_params,
            dataset_params=dataset_params,
            obsprocessors=obsprocessors,
            device=device,
            agent_name=agent_name,
            test_batch_size=test_batch_size,
            receive_batch_dim=receive_batch_dim,
            loss_function=loss_function,
        )
    def set_model(self, input_shape, output_shape):

        """Set the model for the agent to a linear model"""

        from ddopai.approximators import LinearModel

        # flatten time dim of input
        input_size = np.prod(input_shape)
        output_size = output_shape[0]

        self.model = LinearModel(input_size=input_size, output_size=output_size, **self.model_params)

# %% ../../../nbs/30_agents/41_NV_agents/11_NV_erm_agents.ipynb 31
class NewsvendorDLAgent(NVBaseAgent):

    """
    Newsvendor agent implementing Empirical Risk Minimization (ERM) approach 
    based on a deep learning model. 
    """

    def __init__(self, 
                environment_info: MDPInfo,
                dataloader: BaseDataLoader,
                cu: np.ndarray | Parameter,
                co: np.ndarray | Parameter,
                input_shape: Tuple,
                output_shape: Tuple,
                learning_rate_scheduler_params: Dict | None = None,  
                
                # parameters in yaml file
                optimizer_params: dict | None = None,  # default: {"optimizer": "Adam", "lr": 0.01, "weight_decay": 0.0}
                model_params: dict | None = None,  # default: {"hidden_layers": [64, 64], "drop_prob": 0.0, "batch_norm": False, "relu_output": False}
                dataloader_params: dict | None = None,  # default: {"batch_size": 32, "shuffle": True}
                dataset_params: dict | None = None, # parameters needed to convert the dataloader to a torch dataset
                device: str = "cpu", # "cuda" or "cpu"

                obsprocessors: list | None = None,  # default: []
                agent_name: str | None = "DLNV",
                test_batch_size: int = 1024,
                receive_batch_dim: bool = False,
                loss_function: Literal["quantile", "pinball"] = "quantile",
                ):

        # Handle mutable defaults unique to this class
        default_model_params = {
            "hidden_layers": [64, 64],
            "drop_prob": 0.0,
            "batch_norm": False,
            "relu_output": False
            }

        self.model_params = self.update_model_params(default_model_params, model_params or {})

        super().__init__(
            environment_info=environment_info,
            dataloader=dataloader,
            cu=cu,
            co=co,
            input_shape=input_shape,
            output_shape=output_shape,
            optimizer_params=optimizer_params,
            learning_rate_scheduler_params=learning_rate_scheduler_params,
            dataloader_params=dataloader_params,
            dataset_params=dataset_params,
            obsprocessors=obsprocessors,
            device=device,
            agent_name=agent_name,
            test_batch_size=test_batch_size,
            receive_batch_dim=receive_batch_dim,
            loss_function=loss_function,
        )
        
    def set_model(self, input_shape, output_shape):
        
        """Set the model for the agent to an MLP"""

        # flatten time dim of input
        print("input shape", input_shape)
        input_size = np.prod(input_shape)
        output_size = output_shape[0]

        from ddopai.approximators import MLP
        self.model = MLP(input_size=input_size, output_size=output_size, **self.model_params)

# %% ../../../nbs/30_agents/41_NV_agents/11_NV_erm_agents.ipynb 37
class BaseMetaAgent():

    def set_meta_dataloader(
        self, 
        dataloader: BaseDataLoader,
        dataset_params: dict, # parameters needed to convert the dataloader to a torch dataset
        dataloader_params: dict, # dict with keys: batch_size, shuffle
        ) -> None:

        """ """

        dataset = DatasetWrapperMeta(dataloader, **dataset_params)

        self.dataloader = torch.utils.data.DataLoader(dataset, **dataloader_params)

# %% ../../../nbs/30_agents/41_NV_agents/11_NV_erm_agents.ipynb 38
class NewsvendorlERMMetaAgent(NewsvendorlERMAgent, BaseMetaAgent):

    """
    Newsvendor agent implementing Empirical Risk Minimization (ERM) approach 
    based on a linear (regression) model. In addition to the features, the agent
    also gets the sl as input to be able to forecast the optimal order quantity
    for different sl values. Depending on the training pipeline, this model can be 
    adapted to become a full meta-learning algorithm cross products and cross sls.

    """

    def __init__(self, 

                # Parameters for lERM agent
                environment_info: MDPInfo,
                dataloader: BaseDataLoader,
                cu: np.ndarray | Parameter,
                co: np.ndarray | Parameter,
                input_shape: Tuple,
                output_shape: Tuple,
                optimizer_params: dict | None = None,  # default: {"optimizer": "Adam", "lr": 0.01, "weight_decay": 0.0}
                learning_rate_scheduler_params = None,  # TODO: add base class for learning rate scheduler for typing
                model_params: dict | None = None,  # default: {"relu_output": False}
                dataset_params: dict | None = None, # parameters needed to convert the dataloader to a torch dataset
                dataloader_params: dict | None = None,  # default: {"batch_size": 32, "shuffle": True}
                obsprocessors: list | None = None,  # default: []
                device: str = "cpu",  # "cuda" or "cpu"
                agent_name: str | None = "lERMMeta",
                test_batch_size: int = 1024,
                receive_batch_dim: bool = False,
                loss_function: Literal["quantile", "pinball"] = "quantile",
                ):

        self.set_meta_dataloader(dataloader, dataset_params, dataloader_params)

        super().__init__(
            environment_info=environment_info,
            dataloader=dataloader,
            cu=cu,
            co=co,
            input_shape=input_shape,
            output_shape=output_shape,
            optimizer_params=optimizer_params,
            learning_rate_scheduler_params=learning_rate_scheduler_params,
            model_params=model_params,
            dataloader_params=dataloader_params,
            obsprocessors=obsprocessors,
            device=device,
            agent_name=agent_name,
            test_batch_size=test_batch_size,
            receive_batch_dim = receive_batch_dim,
            loss_function=loss_function,
        )

# %% ../../../nbs/30_agents/41_NV_agents/11_NV_erm_agents.ipynb 39
class NewsvendorDLMetaAgent(NewsvendorDLAgent, BaseMetaAgent):

    """
    Newsvendor agent implementing Empirical Risk Minimization (ERM) approach 
    based on a Neural Network. In addition to the features, the agent
    also gets the sl as input to be able to forecast the optimal order quantity
    for different sl values. Depending on the training pipeline, this model can be 
    adapted to become a full meta-learning algorithm cross products and cross sls.

    """

    def __init__(self, 
                environment_info: MDPInfo,
                dataloader: BaseDataLoader,
                cu: np.ndarray | Parameter,
                co: np.ndarray | Parameter,
                input_shape: Tuple,
                output_shape: Tuple,
                learning_rate_scheduler_params = None,  # TODO: add base class for learning rate scheduler for typing
                
                # parameters in yaml file
                optimizer_params: dict | None = None,  # default: {"optimizer": "Adam", "lr": 0.01, "weight_decay": 0.0}
                model_params: dict | None = None,  # default: {"hidden_layers": [64, 64], "drop_prob": 0.0, "batch_norm": False, "relu_output": False}
                dataset_params: dict | None = None, # parameters needed to convert the dataloader to a torch dataset
                dataloader_params: dict | None = None,  # default: {"batch_size": 32, "shuffle": True}
                device: str = "cpu", # "cuda" or "cpu"

                obsprocessors: list | None = None,  # default: []
                agent_name: str | None = "DLNV",
                test_batch_size: int = 1024,
                receive_batch_dim: bool = False,
                loss_function: Literal["quantile", "pinball"] = "quantile",
                ):

        self.set_meta_dataloader(dataloader, dataset_params, dataloader_params)

        super().__init__(
            environment_info=environment_info,
            dataloader=dataloader,
            cu=cu,
            co=co,
            input_shape=input_shape,
            output_shape=output_shape,
            learning_rate_scheduler_params=learning_rate_scheduler_params,

            optimizer_params=optimizer_params,
            model_params=model_params,
            dataloader_params=dataloader_params,
            device=device,

            obsprocessors=obsprocessors,
            agent_name=agent_name,
            test_batch_size=test_batch_size,
            receive_batch_dim=receive_batch_dim,
            loss_function=loss_function,
        )


# %% ../../../nbs/30_agents/41_NV_agents/11_NV_erm_agents.ipynb 40
class NewsvendorDLTransformerAgent(NVBaseAgent):

    """
    Newsvendor agent implementing Empirical Risk Minimization (ERM) approach 
    based on a deep learning model with a Transformer architecture.
    """

    def __init__(self, 
                environment_info: MDPInfo,
                dataloader: BaseDataLoader,
                cu: np.ndarray | Parameter,
                co: np.ndarray | Parameter,
                input_shape: Tuple,
                output_shape: Tuple,
                learning_rate_scheduler_params: Dict | None = None,
                
                # parameters in yaml file
                optimizer_params: dict | None = None,  # default: {"optimizer": "Adam", "lr": 0.01, "weight_decay": 0.0}
                model_params: dict | None = None,  # default: {"max_context_length": 128, "n_layer": 3, "n_head": 8, "n_embd_per_head": 32, "rope_scaling": None, "min_multiple": 256, "gating": True, "drop_prob": 0.0, "final_activation": "identity"}
                dataset_params: dict | None = None, # parameters needed to convert the dataloader to a torch dataset
                dataloader_params: dict | None = None,  # default: {"batch_size": 32, "shuffle": True}
                device: str = "cpu", # "cuda" or "cpu"

                obsprocessors: list | None = None,  # default: []
                agent_name: str | None = "DLNV",
                test_batch_size: int = 1024,
                receive_batch_dim: bool = False,
                loss_function: Literal["quantile", "pinball"] = "quantile",
                ):

        # Handle mutable defaults unique to this class
        default_model_params = {
            "max_context_length": 128,
            "n_layer": 3,
            "n_head": 8,
            "n_embd_per_head": 32,
            "rope_scaling": None,

            "min_multiple": 256,
            "gating": True,

            "drop_prob": 0.0,
            "final_activation": "identity",
            }
        
        self.model_params = self.update_model_params(default_model_params, model_params or {})


        super().__init__(
            environment_info=environment_info,
            dataloader=dataloader,
            cu=cu,
            co=co,
            input_shape=input_shape,
            output_shape=output_shape,
            optimizer_params=optimizer_params,
            learning_rate_scheduler_params=learning_rate_scheduler_params,
            dataset_params=dataset_params,
            dataloader_params=dataloader_params,
            obsprocessors=obsprocessors,
            device=device,
            agent_name=agent_name,
            test_batch_size=test_batch_size,
            receive_batch_dim=receive_batch_dim,
            loss_function=loss_function,
        )
         
    def set_model(self, input_shape, output_shape):
        
        """Set the model for the agent to an MLP"""

        if len(input_shape) == 1:
            raise ValueError("Input shape must be at least 2D for Transformer model")

        output_size = output_shape[0]

        from ddopai.approximators import Transformer
        self.model = Transformer(input_size=input_shape, output_size=output_size, **self.model_params)

# %% ../../../nbs/30_agents/41_NV_agents/11_NV_erm_agents.ipynb 41
class NewsvendorDLTransformerMetaAgent(NewsvendorDLTransformerAgent, BaseMetaAgent):

    """
    Newsvendor agent implementing Empirical Risk Minimization (ERM) approach 
    based on a Neural Network using the attention mechanism. In addition to the features,
    the agent also gets the sl as input to be able to forecast the optimal order quantity
    for different sl values. Depending on the training pipeline, this model can be 
    adapted to become a full meta-learning algorithm cross products and cross sls.

    """

    def __init__(self, 
                environment_info: MDPInfo,
                dataloader: BaseDataLoader,
                cu: np.ndarray | Parameter,
                co: np.ndarray | Parameter,
                input_shape: Tuple,
                output_shape: Tuple,
                learning_rate_scheduler_params: Dict | None = None, 
                
                # parameters in yaml file
                optimizer_params: dict | None = None,  # default: {"optimizer": "Adam", "lr": 0.01, "weight_decay": 0.0}
                model_params: dict | None = None,  # default: {"hidden_layers": [64, 64], "drop_prob": 0.0, "batch_norm": False, "relu_output": False}
                dataset_params: dict | None = None, # parameters needed to convert the dataloader to a torch dataset
                dataloader_params: dict | None = None,  # default: {"batch_size": 32, "shuffle": True}
                device: str = "cpu", # "cuda" or "cpu"

                obsprocessors: list | None = None,  # default: []
                agent_name: str | None = "DLNV",
                test_batch_size: int = 1024,
                receive_batch_dim: bool = False,
                loss_function: Literal["quantile", "pinball"] = "quantile",
                ):

        self.set_meta_dataloader(dataloader, dataset_params, dataloader_params)

        super().__init__(
            environment_info=environment_info,
            dataloader=dataloader,
            cu=cu,
            co=co,
            input_shape=input_shape,
            output_shape=output_shape,
            learning_rate_scheduler_params=learning_rate_scheduler_params,

            optimizer_params=optimizer_params,
            model_params=model_params,
            dataloader_params=dataloader_params,
            device=device,

            obsprocessors=obsprocessors,
            agent_name=agent_name,
            test_batch_size=test_batch_size,
            receive_batch_dim=receive_batch_dim,
            loss_function=loss_function,
        )

