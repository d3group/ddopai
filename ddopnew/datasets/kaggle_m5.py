# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/80_datasets/kaggle_m5.ipynb.

# %% auto 0
__all__ = ['KaggleM5DatasetLoader']

# %% ../../nbs/80_datasets/kaggle_m5.ipynb 3
import logging
logging.basicConfig(level=logging.INFO)

import numpy as np
import os
import pandas as pd

# %% ../../nbs/80_datasets/kaggle_m5.ipynb 4
class KaggleM5DatasetLoader():

    """ Class to download the Kaggle M5 dataset and apply some preprocessing steps
    to prepare it for application in inventory management. """

    def __init__(self, data_path, overwrite=False, product_as_feature=False):
        self.create_paths(data_path)
        self.check_data_path(data_path, overwrite)
        self.product_as_feature = product_as_feature
    
    def load_dataset(self):

        """ Main function to load the dataset. """

        if self.download_data_flag:
            logging.info("Downloading dataset from Kaggle")
            self.download_data()
        else:
            logging.info("Using existing data from disk")
        logging.info("Importing data")
        self.import_from_folder()
        logging.info("Preprocessing data")
        self.preprocess_pipeline()

        return self.demand, self.SKU_features, self.time_features, self.time_SKU_features, self.mask

    def check_data_path(self, data_path, overwrite):

        """ Check if the data path exists and if the data should be downloaded. """

        if not os.path.exists(data_path):
            os.makedirs(data_path)
            self.download_data_flag = True
        else:
            if os.path.exists(self.calendar_path) and os.path.exists(self.sale_path) and os.path.exists(self.price_path):
                self.download_data_flag = True if overwrite else False
            else:
                self.download_data_flag = True

    def create_paths(self, data_path):

        """ Create the paths for the data files. """

        self.data_path = data_path
        self.calendar_path = os.path.join(data_path, "calendar.csv")
        self.sale_path = os.path.join(data_path, "sales_train_evaluation.csv")
        self.price_path = os.path.join(data_path, "sell_prices.csv")

    def preprocess_pipeline(self):
    
        """ Apply simple preprocessing steps to the data. """
        
        logging.info("--Creating catogory mapping and features")  
        self.sale["id"] = self.sale["id"].str.replace("_evaluation", "")
        unique_mapping = self.sale[['item_id', 'dept_id', 'cat_id', 'store_id']].drop_duplicates()
        unique_mapping["SKU_id"] = unique_mapping["item_id"] + "_" + unique_mapping["store_id"]
        unique_mapping["state"] = unique_mapping["store_id"].str.split("_", expand=True)[0]
        unique_mapping.set_index("SKU_id", inplace=True)

        dummy_columns = ["dept_id", "cat_id", "store_id", "state"]
        if self.product_as_feature:
            dummy_columns.append("item_id")
        categories = pd.get_dummies(unique_mapping[dummy_columns], drop_first=True) 

        logging.info("--Preparing sales time series data")
        id = self.sale["id"]
        self.sale = self.sale.iloc[:,6:]
        self.sale["SKU_id"] = id
        self.sale.set_index("SKU_id", inplace=True)
        self.sale = self.sale.transpose()
        self.sale.reset_index(inplace=True, drop=True)
        self.sale.rename_axis(None, axis=1, inplace=True)
        self.sale = self.sale[unique_mapping.index]
        
        logging.info("--Preparing calendric information")
        self.calendar = self.calendar[:1941] # we are only interested in the data we also have sales data for
        self.calendar.drop(["date", "d", "weekday"], axis=1, inplace=True)
        self.calendar["trend"] = np.arange(1, len(self.calendar)+1)
        # For even larger datasets this coule be done at runtime when creating samples, but for this one it should be fine memory-wise
        dummy_columns = ["wday", "month", "event_name_1", "event_type_1", "event_name_2", "event_type_2"]
        self.calendar = pd.get_dummies(self.calendar, columns=dummy_columns, drop_first=True)
        cols = self.calendar.columns.tolist()
        cols.insert(4, cols.pop(1))
        self.calendar = self.calendar[cols]

        # TEMPORARY
        # logging.info("--Preparing snap features")
        # snap_features = self.calendar[["snap_CA", "snap_TX", "snap_WI"]].copy()
        # self.calendar.drop(["snap_CA", "snap_TX", "snap_WI"], axis=1, inplace=True)

        # TEMPORARY
        # new_snap_features = pd.DataFrame(index=range(snap_features.shape[0]), columns=unique_mapping.index)
        # for sku in unique_mapping.index:
        #     state_code = sku.split('_')[-2]
        #     snap_column = f"snap_{state_code}"
        #     new_snap_features[sku] = snap_features[snap_column].values
        # snap_features = new_snap_features

        logging.info("--Preparing price information")
        self.price["SKU_id"] = self.price["item_id"] + "_" + self.price["store_id"]
        self.price.drop(["store_id", "item_id"], axis=1, inplace=True)
        self.price = self.price.pivot_table(index='wm_yr_wk', columns=['SKU_id'], values='sell_price')
        self.price = self.price[unique_mapping.index]

        logging.info("--Creating indicator table if products are available for purchase")
        self.available = self.price.copy()
        self.available = self.available.notnull().astype(int)
        # fill missing values for price (indicated in the available table)
        self.price.fillna(0, inplace=True)

        logging.info("--Preparing final outputs and ensure consistency of time and feature dimensions")
        wm_yr_wk_per_day = self.calendar[["wm_yr_wk"]]
        self.price = self.price.reset_index()
        missing_wm_yr_wk_in_price = wm_yr_wk_per_day[~wm_yr_wk_per_day["wm_yr_wk"].isin(self.price["wm_yr_wk"])]
        if not missing_wm_yr_wk_in_price.empty:
            raise ValueError("The following wm_yr_wk values are in calendar but not in price: ", missing_wm_yr_wk_in_price.tolist())
        self.price = self.price.merge(wm_yr_wk_per_day, on="wm_yr_wk", how="right")
        self.price.drop(["wm_yr_wk"], axis=1, inplace=True)
        self.available = self.available.reset_index()
        self.available = self.available.merge(wm_yr_wk_per_day, on="wm_yr_wk", how="right")
        self.available.drop(["wm_yr_wk"], axis=1, inplace=True)
        # self.calendar.drop(["wm_yr_wk"], axis=1, inplace=True) # TEMPORARY

        price_multi_index = pd.MultiIndex.from_product([['Price'], self.price.columns], names=['Type', 'SKU'])
        self.price.columns = price_multi_index
        time_SKU_features = self.price
        # TEMPORARY
        # snap_multi_index = pd.MultiIndex.from_product([['Snap'], snap_features.columns], names=['DataType', 'SKU'])
        # snap_features.columns = snap_multi_index
        # time_SKU_features = pd.concat([self.price, snap_features], axis=1)
       
        self.demand = self.sale
        self.SKU_features = categories # features that are not time-dependent
        self.time_features = self.calendar # features that are time-dependent
        self.time_SKU_features = time_SKU_features # features taht are time- and SKU-dependent
        self.mask = self.available # A mask that can either mask datapoints during training or be used as a feature

    def import_from_folder(self):
        
        """ Import data from a folder. """

        self.calendar = pd.read_csv(self.calendar_path)
        self.sale = pd.read_csv(self.sale_path)
        self.price = pd.read_csv(self.price_path)
    
    def download_data(self):

        """ Download the data directly from Kaggle. """

        raise NotImplementedError(
            "Download function not implemented yet - please download the data manually\n"
            "from Kaggle and place it in the directory specified in the 'data_path' variable during initialization")
