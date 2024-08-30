# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_utils/11_obsprocessors.ipynb.

# %% auto 0
__all__ = ['BaseProcessor', 'FlattenTimeDimNumpy', 'ConvertDictSpace', 'AddParamsToFeaturesLEGACY', 'AddParamsToFeatures']

# %% ../nbs/00_utils/11_obsprocessors.ipynb 3
from typing import Union, Optional, List, Tuple, Dict

import numpy as np
from .utils import Parameter, check_parameter_types

import torch
import torch.nn as nn
import torch.nn.functional as F

# %% ../nbs/00_utils/11_obsprocessors.ipynb 4
class BaseProcessor():

    def determine_output_shape(self,
        sample_input: Dict, # sample input
        ) -> Tuple | List:

        """
        Determine the output shape based on the input dictionary.
        """

        output = self.__call__(sample_input)

        if isinstance(output, list):
            return [output_element.shape for output_element in output]
        else:
            return output.shape

# %% ../nbs/00_utils/11_obsprocessors.ipynb 5
class FlattenTimeDimNumpy():

    """
    Preprocessor to flatten the time and feature dimension of the input.
    Used, e.g., to convert time-series data for models that cannot process
    a time dimension such as MLPs or Regression models.
    """

    def __init__(self,
        allow_2d: Optional[bool] = False, #
        batch_dim_included: Optional[bool] = True
        ):
        self.allow_2d = allow_2d
        self.batch_dim_included = batch_dim_included

    def check_input(self,
            input: np.ndarray #
            ):
        """
        Check that the input is a Numpy array with the correct shape.
        """
        # Check if the input is a Numpy array
        if not isinstance(input, np.ndarray):
            raise TypeError(f"Expected input to be a numpy array, but got {type(input)} instead.")

        # Determine expected dimensions based on batch_dim_included
        expected_ndim = 3 if self.batch_dim_included else 2
        allow_ndim = 2 if self.batch_dim_included else 1

        # Check if the input array has the correct dimensions
        if input.ndim == expected_ndim:
            # If the input is 3D, it is valid regardless of allow_2d
            return
        elif input.ndim == allow_ndim:
            # If the input has fewer dimensions, check if the reduced dimension is allowed
            if not self.allow_2d:
                raise ValueError(
                    f"Expected input to have {expected_ndim} dimensions with shape "
                    f"{'(batch_size, timesteps, features)' if self.batch_dim_included else '(timesteps, features)'}, "
                    f"but got shape {input.shape} instead. "
                    f"{allow_ndim}D inputs are not allowed when allow_2d is False."
                )
        else:
            # If the input has an unexpected number of dimensions
            expected_shape_msg = (
                f"Expected input to have {expected_ndim} dimensions with shape "
                f"{'(batch_size, timesteps, features)' if self.batch_dim_included else '(timesteps, features)'}"
                if not self.allow_2d
                else f"Expected input to have {expected_ndim} dimensions with shape "
                     f"{'(batch_size, timesteps, features)' if self.batch_dim_included else '(timesteps, features)'} "
                     f"or {allow_ndim} dimensions with shape "
                     f"{'(batch_size, features)' if self.batch_dim_included else '(features)'}"
            )
            raise ValueError(f"{expected_shape_msg}, but got shape {input.shape} instead.")
            
    def __call__(self,
                input: np.ndarray
                ) -> np.ndarray:
                
        """
        Process the input array by keeping the batch dimension and flattening
        the time and feature dimensions.
        """

        # Validate the input tensor
        self.check_input(input)

        if self.batch_dim_included:
            # If batch dimension is included
            if input.ndim == 2:
                output = input
            else:
                # Keep the batch dimension, flatten time and feature dimensions
                batch_size, timesteps, features = input.shape
                output = input.reshape(batch_size, -1)
        else:
            # If batch dimension is not included
            if input.ndim == 1:
                output = input
            else:
                # Flatten time and feature dimensions
                timesteps, features = input.shape
                output = input.reshape(-1)

        return output

# %% ../nbs/00_utils/11_obsprocessors.ipynb 9
class ConvertDictSpace(BaseProcessor):

    """  

    A utility class to process a dictionary of numpy arrays, with options to preserve or flatten the time dimension.

    Note, this class is only used to preprocess output from the environment without batch dimension.
    
    """

    def __init__(self,
        keep_time_dim: Optional[bool] = False, #If time timension should be flattened as well.
        hybrid_space_params: Optional[Dict] = None, # dict with keys "time" that is a list of observation keys that should keep the time dimension.
        ):
        self.keep_time_dim = keep_time_dim
        self.hybrid_space_params = hybrid_space_params

        if not keep_time_dim and hybrid_space_params is not None:
            raise ValueError("If keep_time_dim is False, hybrid_space_params must be None.")
        if hybrid_space_params is not None and not isinstance(hybrid_space_params, dict):
            raise ValueError("hybrid_space_params must be a dictionary if provided.")


    def __call__(self, 
                input: Dict, # Observation as dict of with numpy arrays
                flatten: bool = True, # whether to flatten composite spaces (non-composite spaces will depend on self.keep_time_dim)
                ) -> List[np.ndarray] | np.ndarray: 

        """
        Process the input dictionary by converting it to a numpy array.
        """

        if self.hybrid_space_params is not None:
            obs_2d = [] # time X features
            obs_1d = [] # features
        else:
            obs = [] # features or time X features

        for counter, (key, value) in enumerate(input.items()):
            if not isinstance(value, np.ndarray):
                raise TypeError(f"Expected input to be a dictionary of numpy arrays, but got {type(value)} instead.")

            if self.hybrid_space_params is not None:
                if key in self.hybrid_space_params["time_series_input"]:
                    obs_2d.append(value)
                    if counter != 0:
                        assert obs_2d[counter].shape[0] == obs_2d[counter-1].shape[0], "All time dimensions must be the same."
                else:
                    obs_1d.append(value.flatten())
            else:
                if self.keep_time_dim:
                    obs.append(value)
                    if counter != 0:
                        assert obs[counter].shape[0] == obs[counter-1].shape[0], "All time dimensions must be the same."
                else:
                    obs.append(value.flatten())

        if self.hybrid_space_params is not None:
            obs_2d = np.concatenate(obs_2d, axis=0)
            obs_1d = np.concatenate(obs_1d, axis=0)
            if flatten:
                return np.concatenate([obs_2d.flatten(), obs_1d], axis=0)
            else:
                return [obs_2d, obs_1d]
        else:
            if obs[0].ndim == 1:
                return np.concatenate(obs, axis=0)
            else:
                return np.concatenate(obs, axis=1)

            return np.concatenate(obs, axis=0)

# %% ../nbs/00_utils/11_obsprocessors.ipynb 10
class AddParamsToFeaturesLEGACY(BaseProcessor):

    """  

    A utility class to process a dictionary of numpy arrays, with options to preserve or flatten the time dimension.
    # TODO: Currently is mixes too many cases like batched input, hybrid input etc. Seperate into more specific obsprocessors.

    """

    def __init__(self,
        environment: object, # The environment object, needed to check if val or train mode,
        keep_time_dim: Optional[bool] = False, #If time timension should be flattened as well.
        hybrid: Optional[bool] = False, # If the param dim should be added as separate vector or concatenated to the features.
        receive_batch_dim: Optional[bool] = False, # If the input contains a batch dimension.
        ):

        self.environment = environment
        self.keep_time_dim = keep_time_dim
        self.hybrid = hybrid
        self.receive_batch_dim = receive_batch_dim

        if not keep_time_dim and hybrid:
            raise ValueError("For flattened vector, hybrid should be be merged with features directy.")


    def __call__(self, 
                input: Dict, # Observation as dict of with numpy arrays
                flatten: bool = False, # whether to flatten composite spaces (non-composite spaces will depend on self.keep_time_dim)
                ) -> List[np.ndarray] | np.ndarray: 

        """
        Process the input dictionary by converting it to a numpy array.
        """

        input = input.copy()
        if self.receive_batch_dim:
            features = input["features"]
            print(features.shape)
            if self.environment.mode == "train":
                features = np.expand_dims(features, axis=0)
                
            if not self.keep_time_dim:
                batch_size, time_steps, feature_dims = features.shape
                new_shape = (batch_size, time_steps*feature_dims)
                features = features.reshape(new_shape)
        else:
            features = input["features"] if self.keep_time_dim else input["features"].flatten()
        del input["features"]

        if self.hybrid:
            if receive_batch_dim:
                raise NotImplementedError("Hybrid not implemented yet for batched input.")
            else:
                obs_1d = [] # features or time X features
                obs_2d = [] # time X features
                obs.append(input["features"])
        
        for counter, (key, value) in enumerate(input.items()):
            if not isinstance(value, np.ndarray):
                raise TypeError(f"Expected input to be a dictionary of numpy arrays, but got {type(value)} instead.")
            
            if value.ndim == 1:
                if features.ndim == 1:
                    features = np.concatenate([features, value])
                else:
                    if self.hybrid:
                        raise NotImplementedError("Hybrid not implemented yet.")
                    # expand value to 2d by copy time dimension
                    else:
                        if self.receive_batch_dim:

                            if features.ndim == 3: # then it is (batch x time x features)
                                value = np.expand_dims(value, axis=0) # add batch dimension
                                value = np.expand_dims(value, axis=1) # add time dimension

                                value = np.repeat(value, features.shape[1], axis=1) # repeat for all time steps
                        
                            else:
                                value = np.expand_dims(value, axis=0) # add batch dimension

                            features = np.concatenate([features, value], axis=-1) # concatenate along feature dimension

                        else:
                            value = np.expand_dims(value, axis=0)
                            value = np.repeat(value, features.shape[0], axis=0)

                            features = np.concatenate([features, value.flatten()])
            
            else:
                if value.shape == features.shape:
                    features = np.concatenate([features, value.flatten()])
                else:
                    raise ValueError(f"Expected input to have the same shape as features, but got {value.shape} instead (feature shape: {features.shape}).")
        
        if self.environment.mode == "train":
            if len(features.shape) == 3:
                features = np.squeeze(features, axis=0) # remove batch dimension
                
        if self.hybrid:
            if flatten:
                raise NotImplementedError("Hybrid not implemented yet.")
            else:
                raise NotImplementedError("Hybrid not implemented yet.")
        else:
            return features
            

# %% ../nbs/00_utils/11_obsprocessors.ipynb 11
class AddParamsToFeatures(BaseProcessor):

    """

    A utility class to process a dictionary of numpy arrays (from dict space), with options to preserve or flatten the time dimension.
    It always adds the parameters to the appropriate dimension. For composite spaces (partially time-series, partially not), use the
    separate AddParamsToFeaturesComposite class.
    
    """

    def __init__(self,
        environment: object, # The environment object, needed to check if val or train mode,
        keep_time_dim: Optional[bool] = False, #If time timension should be flattened as well.
        receive_batch_dim: Optional[bool] = False, # If the input contains a batch dimension.
        ):

        self.environment = environment
        self.keep_time_dim = keep_time_dim
        self.receive_batch_dim = receive_batch_dim

    def __call__(self, 
                input: Dict, # Observation as dict of with numpy arrays
                ) -> List[np.ndarray] | np.ndarray: 

        """
        Process the input dictionary by converting it to a numpy array.
        """

        input = input.copy()
        if self.receive_batch_dim:
            features = input["features"]
                
            if not self.keep_time_dim:
                batch_size, time_steps, feature_dims = features.shape
                new_shape = (batch_size, time_steps*feature_dims)
                features = features.reshape(new_shape)
        else:
            features = input["features"] if self.keep_time_dim else input["features"].flatten()
        del input["features"]
        
        for counter, (key, value) in enumerate(input.items()):
            if not isinstance(value, np.ndarray):
                raise TypeError(f"Expected input to be a dictionary of numpy arrays, but got {type(value)} instead.")
            
            value_shape = value.shape

            if value.ndim == 1:
                if features.ndim == 1:
                    features = np.concatenate([features, value])
                else:
                    if self.receive_batch_dim:

                        if features.ndim == 3: # then it is (batch x time x features)
                            value = np.expand_dims(value, axis=-1) # add value dim (first is batch dim)
                            value = np.expand_dims(value, axis=1) # add time dimension

                            # TODO: check if it always should expand the features dimension
                            if value.shape[0] == 1 and features.shape[0] > 1:
                                value = np.repeat(value, features.shape[0], axis=0)
                            value = np.repeat(value, features.shape[1], axis=1) # repeat for all time steps
                    
                        else:
                            value = np.expand_dims(value, axis=-1) # add value dim (first is batch dim)
                            # TODO: check if it always should expand the features dimension
                            if value.shape[0] == 1 and features.shape[0] > 1:
                                value = np.repeat(value, features.shape[0], axis=0) # repeat for batch

                        features = np.concatenate([features, value], axis=-1) # concatenate along feature dimension

                    else:

                        if features.ndim == 2: # then it is (time x features)
                            value = np.expand_dims(value, axis=0)
                            value = np.repeat(value, features.shape[0], axis=0)

                        features = np.concatenate([features, value.flatten()], axis=-1)
            
            else:
                if value.shape == features.shape:
                    features = np.concatenate([features, value.flatten()])
                else:
                    raise ValueError(f"Expected input to have the same shape as features, but got {value.shape} instead (feature shape: {features.shape}).")

        return features
            
