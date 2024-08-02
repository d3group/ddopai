# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/f_10_dataloaders/12_tabular_dataloaders.ipynb.

# %% auto 0
__all__ = ['XYDataLoader']

# %% ../../nbs/f_10_dataloaders/12_tabular_dataloaders.ipynb 3
import numpy as np
from abc import ABC, abstractmethod
from typing import Union

from .base import BaseDataLoader

# %% ../../nbs/f_10_dataloaders/12_tabular_dataloaders.ipynb 4
class XYDataLoader(BaseDataLoader):
    
    def __init__(self,
        X: np.ndarray,
        Y: np.ndarray,
        val_index_start: Union[int, None] = None, # give list
        test_index_start: Union[int, None] = None, # give list
        lag_window_params: Union[dict] = None # default: {'lag_window': None, 'include_y': False, 'pre-calc': False}
    ):



        self.X = X
        self.Y = Y

        self.val_index_start = val_index_start
        self.test_index_start = test_index_start

        if self.val_index_start is not None:
            self.train_index_end = self.val_index_start-1
        elif self.test_index_start is not None:
            self.train_index_end = self.test_index_start-1
        else:
            self.train_index_end = len(Y)-1

        self.dataset_type = "train"

        lag_window_params = lag_window_params or {'lag_window': None, 'include_y': False, 'pre-calc': False}

        self.prep_lag_features(lag_window_params)

  
        if len(X.shape) == 1:
            self.X = X.reshape(-1, 1)
        
        if len(Y.shape) == 1:
            self.Y = Y.reshape(-1, 1)

        assert len(X) == len(Y), 'X and Y must have the same length'

        self.num_units = Y.shape[1] # shape 0 is alsways time, shape 1 is the number of units (e.g., SKUs)

        super().__init__()

    def prep_lag_features(self, lag_window_params: dict):
        # handle lag window for data
        # to be discussed: Do we need option to only provide lag demand wihtout lag features?
        self.lag_window = lag_window_params['lag_window']
        self.include_y = lag_window_params['include_y']
        self.pre_calc = lag_window_params['pre-calc']

        if self.pre_calc:
            if self.include_y:
                # add additional column to X with demand shifted by 1
                self.X = np.concatenate((self.X, np.roll(self.Y, 1, axis=0)), axis=1)
                self.X = self.X[1:] # remove first row
                self.Y = self.Y[1:] # remove first row
                
                self.val_index_start = self.val_index_start-1
                self.test_index_start = self.test_index_start-1
                self.train_index_end  = self.train_index_end-1
        
            if self.lag_window is not None and self.lag_window > 0:

                # add lag features as dimention 2 to X (making it dimension (datapoints, sequence_length, features))
                X_lag = np.zeros((self.X.shape[0], self.lag_window+1, self.X.shape[1]))
                for i in range(self.lag_window+1):
                    if i == 0:
                        features = self.X
                    else:    
                        features = self.X[:-i, :]
                    X_lag[i:, self.lag_window-i, :] = features
                self.X = X_lag[self.lag_window:]
                self.Y = self.Y[self.lag_window:]

                self.val_index_start = self.val_index_start-self.lag_window
                self.test_index_start = self.test_index_start-self.lag_window
                self.train_index_end  = self.train_index_end-self.lag_window

        else:
            self.lag_window = None
            self.include_y = False

                # add time dimension to X
    
    def __getitem__(self, idx): 

        if self.dataset_type == "train":
            if idx > self.train_index_end:
                raise IndexError(f'index{idx} out of range{self.train_index_end}')
            idx = idx

        elif self.dataset_type == "val":
            idx = idx + self.val_index_start
            
            if idx >= self.test_index_start:
                raise IndexError(f'index{idx} out of range{self.test_index_start}')
            
        elif self.dataset_type == "test":
            idx = idx + self.test_index_start
            
            if idx >= len(self.X):
                raise IndexError(f'index{idx} out of range{len(self.X)}')
        
        else:
            raise ValueError('dataset_type not set')

        return self.X[idx], self.Y[idx]

    def __len__(self):
        return len(self.X)
    
    @property
    def X_shape(self):
        return self.X.shape
    
    @property
    def Y_shape(self):
        return self.Y.shape

    @property
    def len_train(self):
        return self.train_index_end+1

    @property
    def len_val(self):
        if self.val_index_start is None:
            raise ValueError('no validation set defined')
        return self.test_index_start-self.val_index_start

    @property
    def len_test(self):
        if self.test_index_start is None:
            raise ValueError('no test set defined')
        return len(self.Y)-self.test_index_start

    def get_all_X(self,
                dataset_type: str = 'train' # can be 'train', 'val', 'test', 'all'
                ): 

        """
        Returns the entire features dataset. If no X data is available, return None.
        """

        if dataset_type == 'train':
            return self.X[:self.val_index_start].copy() if self.X is not None else None
        elif dataset_type == 'val':
            return self.X[self.val_index_start:self.test_index_start].copy() if self.X is not None else None
        elif dataset_type == 'test':
            return self.X[self.test_index_start:].copy() if self.X is not None else None
        elif dataset_type == 'all':
            return self.X.copy() if self.X is not None else None
        else:
            raise ValueError('dataset_type not recognized')

    def get_all_Y(self,
                dataset_type: str = 'train' # can be 'train', 'val', 'test', 'all'
                ): 

        """
        Returns the entire target dataset. If no Y data is available, return None.
        """

        if dataset_type == 'train':
            return self.Y[:self.val_index_start].copy() if self.Y is not None else None
        elif dataset_type == 'val':
            return self.Y[self.val_index_start:self.test_index_start].copy() if self.Y is not None else None
        elif dataset_type == 'test':
            return self.Y[self.test_index_start:].copy() if self.Y is not None else None
        elif dataset_type == 'all':
            return self.Y.copy() if self.Y is not None else None
        else:
            raise ValueError('dataset_type not recognized')
        
