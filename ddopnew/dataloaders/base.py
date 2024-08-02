# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/f_10_dataloaders/10_base_dataloader.ipynb.

# %% auto 0
__all__ = ['BaseDataLoader']

# %% ../../nbs/f_10_dataloaders/10_base_dataloader.ipynb 3
import numpy as np
from abc import ABC, abstractmethod
from typing import Union

# %% ../../nbs/f_10_dataloaders/10_base_dataloader.ipynb 4
class BaseDataLoader(ABC):
   
    """
    Base class for data loaders.
    The idea of the data loader is to provide all external information to the environment
    (including lagged data, demand etc.). Internal data influenced by past decisions (like
    inventory levels) is to be added from within the environment
    """

    def __init__(self):
        self.dataset_type = "train"

    @abstractmethod
    def __len__(self):
        '''
        Returns the length of the dataset. For dataloaders based on distributions, this 
        should return an error that the length is not defined, otherwise it should return
        the number of samples in the dataset.
        '''
        pass

    @abstractmethod   
    def __getitem__(self, idx):

        """
        Returns always a tuple of X and Y data. If no X data is available, return None.
        """
        pass

    @property
    @abstractmethod
    def X_shape(self):
        """
        Returns the shape of the X data.
        It should follow the format (n_samples, n_features). If the data has a time dimension with
        a fixed length, the shape should be (n_samples, n_time_steps, n_features). If the data is 
        generated from a distribtition, n_samples should be set to 1.
        """
        pass

    @property
    @abstractmethod
    def Y_shape(self):
        """
        Returns the shape of the Y data.
        It should follow the format (n_samples, n_SKUs). If the variable of interst is only a single
        SKU, the shape should be (n_samples, 1). If the data is 
        generated from a distribtition, n_samples should be set to 1.
        """
        pass

    @abstractmethod   
    def get_all_X(self):

        """
        Returns the entire features dataset. If no X data is available, return None.
        """
        pass    

    @abstractmethod   
    def get_all_Y(self):

        """
        Returns the entire target dataset. If no Y data is available, return None.
        """
        pass  

    def val(self):

        if self.val_index_start is None:
            raise ValueError('no validation set defined')
        else:
            self.dataset_type = "val"

    def test(self):

        if self.test_index_start is None:
            raise ValueError('no test set defined')
        else:
            self.dataset_type = "test"
    
    def train(self):

        self.dataset_type = "train"
