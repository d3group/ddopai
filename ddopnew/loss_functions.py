# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_utils/00_loss_functions.ipynb.

# %% auto 0
__all__ = ['pinball_loss']

# %% ../nbs/00_utils/00_loss_functions.ipynb 3
import numpy as np
from .utils import Parameter

# %% ../nbs/00_utils/00_loss_functions.ipynb 5
def pinball_loss(y_true, y_pred, underage_cost, overage_cost):

    if isinstance(underage_cost, Parameter):
        underage_cost = underage_cost.get_value()
    if isinstance(overage_cost, Parameter):
        overage_cost = overage_cost.get_value()
    
    loss = np.maximum(y_true - y_pred, 0) * underage_cost + np.maximum(y_pred - y_true, 0) * overage_cost

    return loss
