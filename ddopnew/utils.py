# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/000_utils_utils.ipynb.

# %% auto 0
__all__ = ['check_parameter_types', 'Parameter', 'MDPInfo', 'DatasetWrapper']

# %% ../nbs/000_utils_utils.ipynb 3
import numpy as np

from torch.utils.data import Dataset

from typing import Union, List, Tuple

# %% ../nbs/000_utils_utils.ipynb 5
def check_parameter_types(*args, parameter_type=np.ndarray):
    """
    Checks if each argument in args is of the specified type, defaulting to np.ndarray.

    Parameters:
    - parameter_type: The expected type for each argument, default is np.ndarray.
    - args: A variable number of arguments to check.

    Raises:
    - TypeError: If any argument is not of the expected type.
    """
    for index, arg in enumerate(args):
        if not isinstance(arg, parameter_type):
            raise TypeError(f"Argument {index+1} of {len(args)} is of type {type(arg).__name__}, expected {parameter_type.__name__}")

# %% ../nbs/000_utils_utils.ipynb 7
class Parameter():

    """
    Simple class to handle parameters in the environment. The advantage of this class is that it can be
    used to set parameters that may change over time and accessed by multiple objects such as the 
    environment, agent or dataloaders.
    """
    
    def __init__(self,
                value: Union[int, float, List[int], List[float], np.ndarray],
                min_value: Union[int, float, List[int], List[float], np.ndarray] = None,
                max_value: Union[int, float, List[int], List[float], np.ndarray] = None,
                shape: Tuple[int] = (1,)):

        self._min_value = min_value
        self._max_value = max_value
        
        self.set_value(value, shape)

    def __call__(self):
        """
        Update and return the parameter in the provided index.

        Args:
             *idx (list): index of the parameter to return.

        Returns:
            The updated parameter in the provided index.

        """
        return self.get_value()

    def get_value(self):
        """
        Return the current value of the parameter in the provided index.

        Args:
            *idx (list): index of the parameter to return.

        Returns:
            The current value of the parameter in the provided index.

        """

        return self._value

    def set_value(self, 
                    value: Union[int, float, List[int], List[float], np.ndarray],
                    shape: Tuple[int] = (1,)):
       
        """
        Set the value of the parameter.

        Args:
            value (float, int, numpy array): The value to set the parameter to.

        """

        if isinstance(value, (int, float)):
            self._value = np.array([value])
            self._value.reshape(shape)
        
        elif isinstance(value, list):
            value = np.array(value)
            assert value.shape == shape, "Shape of value must be the same as the shape of the parameter"
            self._value = value
        
        elif isinstance(value, np.ndarray):
            assert value.shape == shape, "Shape of value must be the same as the shape of the parameter"
            self._value = value
        
        else:
            raise ValueError("Value must be a scalar or numpy array")

        if self._min_value is not None:
            self._value = np.maximum(self._value, self._min_value)
        if self._max_value is not None:
            self._value = np.minimum(self._value, self._max_value)

    @property
    def shape(self):
        """
        Returns:
            The shape of the table of parameters.
        """
        return self._value.shape
    
    @property
    def size(self):
        """
        Returns:
            The size of the table of parameters.
        """
        return self._value.size 

# %% ../nbs/000_utils_utils.ipynb 9
class MDPInfo():
    """
    This class is used to store the information of the environment.
    It is based on MushroomRL (https://github.com/MushroomRL)
    """
    
    def __init__(self, observation_space, action_space, gamma, horizon, dt=1e-1, backend='numpy'):
        """
        Constructor.

        Args:
             observation_space ([Box, Discrete]): the state space;
             action_space ([Box, Discrete]): the action space;
             gamma (float): the discount factor;
             horizon (int): the horizon;
             dt (float, 1e-1): the control timestep of the environment;
             backend (str, 'numpy'): the type of data library used to generate state and actions.

        """
        self.observation_space = observation_space
        self.action_space = action_space
        self.gamma = gamma
        self.horizon = horizon
        self.dt = dt
        self.backend = backend

    @property
    def size(self):
        """
        Returns:
            The sum of the number of discrete states and discrete actions. Only works for discrete spaces.

        """
        return self.observation_space.size + self.action_space.size

    @property
    def shape(self):
        """
        Returns:
            The concatenation of the shape tuple of the state and action spaces.

        """
        return self.observation_space.shape + self.action_space.shape

# %% ../nbs/000_utils_utils.ipynb 10
class DatasetWrapper(Dataset):
    """
    This class is used to wrap a Pytorch Dataset around the ddopnew dataloader
    to enable the usage of the Pytorch Dataloader during training
    
    """

    def __init__(self, dataloader):
        """
        Constructor.

        Args:
             dataset (ddopnew.data.dataset): the dataset to wrap.

        """
        self.dataloader = dataloader
    
    def __getitem__(self, idx):
        """
        Get the item at the provided index.

        Args:
             idx (int): the index of the item to get.

        Returns:
            The item at the provided index.

        """

        # create tuple of items
        return self.dataloader[idx]


    def __len__(self):
        
        if self.dataloader.dataset_type == 'train':
            return self.dataloader.len_train
        elif self.dataloader.dataset_type == 'val':
            return self.dataloader.len_val
        elif self.dataloader.dataset_type == 'test':
            return self.dataloader.len_test
        else:
            raise ValueError("Dataset type must be either 'train', 'val' or 'test'")
