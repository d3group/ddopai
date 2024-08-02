# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/80_datasets/datasets.ipynb.

# %% auto 0
__all__ = ['get_all_release_tags', 'get_release_tag', 'get_dataset_url', 'get_asset_url', 'download_file_from_github',
           'unzip_file', 'load_data_from_directory', 'DatasetLoader']

# %% ../nbs/80_datasets/datasets.ipynb 3
import numpy as np
import logging
import requests
import os
import re
import pandas as pd
import zipfile


# %% ../nbs/80_datasets/datasets.ipynb 6
def get_all_release_tags():

    url = f"https://api.github.com/repos/opimwue/ddopnew/releases"
    response = requests.get(url)
    
    if response.status_code == 200:
        releases = response.json()
        tags = [release['tag_name'] for release in releases]
        return tags
    else:
        raise ValueError(f"Failed to fetch releases: {response.status_code} with message: {response.text}")

def get_release_tag(dataset_type, version):

    release_tags = get_all_release_tags()
    release_tags_filtered = [tag for tag in release_tags if dataset_type in tag]

    if version == "latest":
        release_tags_filtered.sort(key=lambda x: [int(num) if num.isdigit() else num for num in re.findall(r'\d+|\D+', x.split('_v')[-1])])
        release_tag = release_tags_filtered[-1]
    else:
        release_tag = f"{dataset_type}_{version}"
    
    return release_tag
    
    print(f"Filtered release tags: {release_tags_filtered}")



def get_dataset_url(dataset_type, dataset_number, release_tag):
    # Define the repository and release tag

    # GitHub API URL for the release
    api_url = f"https://api.github.com/repos/opimwue/ddopnew/releases/tags/{release_tag}"
    
    # Make the request to the GitHub API
    response = requests.get(api_url)

    # Check if the request was successful
    if response.status_code == 200:
        release_info = response.json()
        assets = release_info.get("assets", [])

        # get asset where the name contains the f"{dataset_type}_dataset_{dataset_number}"
        assets = [asset for asset in assets if f"{dataset_type}_dataset_{dataset_number}_" in asset['name']]

        for asset in assets:
            logging.debug(f"Found dataset: {asset['name']}")

        if len(assets) == 0:
            raise ValueError(f"Dataset {dataset_type}_dataset_{dataset_number} not found in release {release_tag}")
        elif len(assets) > 1:
            raise ValueError(f"Multiple datasets found for {dataset_type}_dataset_{dataset_number} in release {release_tag}")
        else:
            asset = assets[0]
            return asset['browser_download_url']
    else:
        raise ValueError(f"Failed to fetch release information: {response.status_code}")

def get_asset_url(dataset_type, dataset_number, version="latest"):

    release_tag = get_release_tag(dataset_type, version)

    asset_url = get_dataset_url(dataset_type, dataset_number, release_tag)

    return asset_url


def download_file_from_github(url, output_path):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(output_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file.write(chunk)
        logging.debug(f"File downloaded successfully: {output_path}")
    else:
        logging.error(f"Failed to download file: {response.status_code}")

def unzip_file(zip_file_path, output_dir, delete_zip_file=True):

    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(output_dir)

    if delete_zip_file:
        os.remove(zip_file_path)


def load_data_from_directory(dir):

    data = list()
    for file in os.listdir(dir):
        # check if the file is a csv, pkl, or numpy file
        # load data into pandas dataframe array with name of the file before the extension

        if file.endswith(".csv"):
            data.append(pd.read_csv(os.path.join(dir, file)))
        elif file.endswith(".pkl"):
            data.append(pd.read_pickle(os.path.join(dir, file)))
        elif file.endswith(".npy"):
            data.append(np.load(os.path.join(dir, file)))
        else:
            raise ValueError(f"File {file} is not a valid file type (csv, pkl, or npy)")
    
    return data

# %% ../nbs/80_datasets/datasets.ipynb 8
class DatasetLoader():

    """
    Class to load datasets from the GitHub repository.
    """

    dataset_types_univariate = [
    ]

    dataset_types_multivariate = [
        "arma_10_10",
        "arma_2_2",
        "ar_1",
    ]
    
    def __init__(self):
        pass
    
    def show_dataset_types(self,
            show_num_datasets_per_type=False # Whether to show the number of datasets per type
            ):

        """ Show an overview of all dataset types available in the repository."""

        if show_num_datasets_per_type:
            raise NotImplementedError("show_num_datasets_per_type is not implemented yet.")
        else:
            print("Univariate datasets:")
            for dataset in DatasetLoader.dataset_types_univariate:
                print(dataset)
            
            print("\nMultivariate datasets:")
            for dataset in DatasetLoader.dataset_types_multivariate:
                print(dataset)
        
    def load_dataset(self,
        dataset_type: str,
        dataset_number: int,
        overwrite: bool = False, # Whether to overwrite the dataset if it already exists
        version: str = "latest", # Which version of the dataset to load, "latest" or a specific version
    ):

        """ Load a dataset from the GitHub repository."""

        if dataset_type not in self.dataset_types_univariate and dataset_type not in self.dataset_types_multivariate:
            raise ValueError(f"Dataset type {dataset_type} is not valid. Use the function show_dataset_types() to see valid dataset types.")

        asset_url = get_asset_url(dataset_type, dataset_number, version=version)


        # check if folder "data" exists, if not create it
        if not os.path.exists("data"):
            os.makedirs("data")

        output_file_path = f"data/{dataset_type}_dataset_{dataset_number}"

        download = False
        # check if the dataset has already been downloaded
        if os.path.exists(output_file_path):
            logging.warning(f"Dataset {dataset_type}_dataset_{dataset_number} has already been downloaded.")
            if overwrite:
                logging.warning("Overwriting dataset.")
                download = True
            else:
                logging.warning("Keeping existing dataset.")
        else:
            download = True

        if download:
            download_file_from_github(asset_url, output_file_path+".zip")
            unzip_file(output_file_path+".zip", output_file_path)

        data = load_data_from_directory(output_file_path)

        return data
