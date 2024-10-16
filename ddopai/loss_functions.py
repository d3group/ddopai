"""Numpy-based loss functans that can be used by environments or non-pytorch models."""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_utils/20_loss_functions.ipynb.

# %% auto 0
__all__ = ['pinball_loss', 'quantile_loss']

# %% ../nbs/00_utils/20_loss_functions.ipynb 3
from typing import Union, Optional

import numpy as np
from .utils import Parameter, check_parameter_types

import torch
import torch.nn as nn
import torch.nn.functional as F

# %% ../nbs/00_utils/20_loss_functions.ipynb 4
def pinball_loss(
            Y_true: np.ndarray, 
            Y_pred: np.ndarray,
            underage_cost: Parameter | np.ndarray,
            overage_cost: Parameter | np.ndarray,
            ) -> np.ndarray: # returns the cost per observation

    """

    Pinball loss calculating the cost of underestimating and overestimating the target value
    based on specific underage and overage costs. Used to evaulate the Newsvendor cost.

    """

    if isinstance(underage_cost, Parameter):
        underage_cost = underage_cost.get_value()
    if isinstance(overage_cost, Parameter):
        overage_cost = overage_cost.get_value()

    check_parameter_types(Y_true, Y_pred, underage_cost, overage_cost)

    # assert shapes
    assert Y_true.shape == Y_pred.shape, f"y_true and y_pred must have the same shape, but got {Y_true.shape} and {Y_pred.shape}"

    loss = np.maximum(Y_true - Y_pred, 0) * underage_cost + np.maximum(Y_pred - Y_true, 0) * overage_cost

    return loss

# %% ../nbs/00_utils/20_loss_functions.ipynb 6
def quantile_loss(
                Y_true: np.ndarray,
                Y_pred: np.ndarray,
                quantile: Union[float, Parameter],
                ) -> np.ndarray: # returns the cost per observation

    """
    Similar evaluation function to the pinball loss, but with the quantile of range
    [0, 1] as a parameter instead of SKU-specific cost levels for underage and overage.

    """

    if isinstance(quantile, Parameter):
        quantile = quantile.get_value()

    check_parameter_types(Y_true, Y_pred, quantile)
    
    # assert shapes
    assert Y_true.shape == Y_pred.shape, f"y_true and y_pred must have the same shape, but got {Y_true.shape} and {Y_pred.shape}"
    
    loss = np.maximum((Y_true - Y_pred) * quantile, (Y_pred - Y_true) * (1 - quantile))

    return loss


