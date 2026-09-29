"""
Parameter Space Generator for Autonomous Laboratory

Generates and manages parameter spaces for reaction space exploration.
Supports random and Latin hypercube sampling for train/test/validation splits.
"""

import copy
import json
import os
import pickle
import random
import sys
from functools import reduce
from json import encoder

import numpy as np
import pandas as pd
from tqdm import tqdm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from Algorithm.Bayesian.target_space import DiscreteSpace, TargetSpace

encoder.FLOAT_REPR = lambda o: format(o, ".2f")


class Template:
    """Base template for labeling data structure."""

    def __init__(self):
        self.labeling_template = {
            "from": None,
            "cycle": None,
            "coordination": [],
            "label": None,
            "strategy": "",
            "confidence": 0,
            "logit": 0,
        }


class FileManager:
    """File I/O utilities for JSON and pickle data."""

    def save_data(self, filepath, data):
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)

    def load_data(self, filepath):
        if not os.path.isfile(filepath):
            data = []
            self.save_data(filepath, data)

        with open(filepath) as f:
            data = json.load(f)
        return data

    def save_model(self, model_path, model):
        with open(model_path, "wb") as fw:
            pickle.dump(model, fw)

    def load_model(self, model_path):
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        return model


class ParameterSpace(Template, FileManager):
    """
    Parameter space generator for autonomous laboratory experiments.

    Generates candidate points, creates labeling sets, and splits data
    into train/test/validation sets using random or Latin hypercube sampling.
    """

    def __init__(self, configfile):
        Template.__init__(self)
        FileManager.__init__(self)

        self.DILUTE_PRECISION = 0.01
        self.DILUTE_LIMIT = 1
        self.VOLUME_PRECISION = 1
        self.VOLUME_LIMIT = 100
        self.MEMORY = 1

        self.configfile = configfile

        self.UNLABELED_DATA_DIR = configfile["metadata"]["saveDirPath"]
        self.SPLIT_DATA_DIR = configfile["algorithm"]["splitDataDir"]
        self.INITIAL_DATA_NUM = configfile["algorithm"]["initialDataNum"]
        self.EVAL_DATA_NUM = configfile["algorithm"]["evaluationDataNum"]
        self.SAMPLING_OPTION = configfile["algorithm"]["sampling_method"]
        self.PARAM_NAME = list(configfile["algorithm"]["prangeDict"].keys())
        self.SEED_NUM = self.configfile["algorithm"]["randomState"]
        self.PRANGE = self.configfile["algorithm"]["prangeDict"]

        self.pbounds = {
            item[0]: (item[1][:2])
            for item in sorted(self.PRANGE.items(), key=lambda x: x[0])
        }
        self._space_train = TargetSpace(
            target_func=None, pbounds=self.pbounds, random_state=self.SEED_NUM + 12541
        )
        self._real_space_train = DiscreteSpace(
            target_func=None, prange=self.PRANGE, random_state=self.SEED_NUM + 12541
        )
        self._space_eval = TargetSpace(
            target_func=None, pbounds=self.pbounds, random_state=self.SEED_NUM + 1251
        )
        self._real_space_eval = DiscreteSpace(
            target_func=None, prange=self.PRANGE, random_state=self.SEED_NUM + 1251
        )
        self._space_valid = TargetSpace(
            target_func=None, pbounds=self.pbounds, random_state=self.SEED_NUM + 125
        )
        self._real_space_valid = DiscreteSpace(
            target_func=None, prange=self.PRANGE, random_state=self.SEED_NUM + 125
        )

    def _multiply_all(self, a, b):
        return a * b

    def _calculate_each_space_size_list(self, space_lists):
        space_len_list = []
        for info in space_lists:
            space_len_list.append((info[1] - info[0] + info[2]) / info[2])
        return space_len_list

    def _calculate_total_space_size(self, space_lists):
        space_len_list = self._calculate_each_space_size_list(space_lists)
        return int(reduce(self._multiply_all, space_len_list))

    def _idx_to_value(self, space_idx, space_lists=[(1, 100, 1), (1, 100, 1)]):
        space_len_list = self._calculate_each_space_size_list(space_lists)
        index_value = []
        for param in range(len(space_len_list) - 1):
            index_value.append(
                float(
                    space_lists[param][0]
                    + (
                        space_idx
                        // (reduce(self._multiply_all, space_len_list[param + 1 :]))
                        % (space_len_list[param])
                        * space_lists[param][2]
                    )
                )
            )
        index_value.append(
            float(
                space_lists[len(space_len_list) - 1][0]
                + (space_idx % space_len_list[-1])
                * space_lists[len(space_len_list) - 1][2]
            )
        )
        return index_value

    def _calc_euclidean(self, list1, list2):
        squared_dist = 0
        for i in range(len(list1)):
            squared_dist += (list1[i] - list2[i]) ** 2
        return np.sqrt(squared_dist)

    def _normalize(self, data, prange_list):
        data = np.array(data)
        for i in range(data.shape[1]):
            data[:, i] = (data[:, i] - prange_list[i][0]) / (
                prange_list[i][1] - prange_list[i][0]
            )
        return data.tolist()

    def make_candidates(self, space_lists=[(1, 100, 1), (1, 100, 1)]):
        """
        Generate candidate points from parameter space.

        Args:
            space_lists: List of (min, max, step) tuples for each parameter
        """
        space_len_list = self._calculate_each_space_size_list(space_lists)
        parameter_space_size = int(reduce(self._multiply_all, space_len_list))

        for idx in range(parameter_space_size // self.MEMORY):
            unlabeled_data = []
            for i in range(self.MEMORY):
                space_idx = idx * self.MEMORY + i
                index_value = self._idx_to_value(space_idx, space_lists=space_lists)
                unlabeled_data.append(index_value)
            yield unlabeled_data

        if int(parameter_space_size % self.MEMORY) != 0:
            unlabeled_data = []
            for i in range(parameter_space_size % self.MEMORY):
                space_idx = (parameter_space_size // self.MEMORY) * self.MEMORY + i
                index_value = self._idx_to_value(space_idx, space_lists=space_lists)
                unlabeled_data.append(index_value)
            yield unlabeled_data

    def make_labeling_set(self):
        """Create and save the complete parameter space as JSON."""
        space_list = list(self.configfile["algorithm"]["prangeDict"].values())
        normalized_space_lists = [
            (0, 1, interval / (max_val - min_val))
            for min_val, max_val, interval in space_list
        ]
        parameter_space_size = self._calculate_total_space_size(
            space_lists=normalized_space_lists
        )
        candidates_set = self.make_candidates(space_lists=normalized_space_lists)
        candidates = next(candidates_set)
        unlabeled_data = []

        for _ in tqdm(
            range(parameter_space_size // self.MEMORY - 1), desc="load_candidate"
        ):
            for idx in range(self.MEMORY):
                candidates.append(next(candidates_set)[idx])

        if int(parameter_space_size % self.MEMORY) != 0:
            for idx in range(parameter_space_size % self.MEMORY):
                candidates.append(next(candidates_set)[idx])

        for i in tqdm(range(len(candidates)), desc="converting"):
            for j in range(len(candidates[0])):
                candidates[i][j] = float(candidates[i][j])

        for idx in tqdm(range(len(candidates)), desc="empty_formating"):
            temp_unlabeled = copy.deepcopy(self.labeling_template)
            unlabeled_data.append(temp_unlabeled)

        for idx, value in tqdm(enumerate(unlabeled_data), desc="fill_fomating"):
            value["from"] = ""
            value["coordination"] = candidates[idx]
            value["label"] = None
            value["strategy"] = None
            value["confidence"] = {"react": 0, "not react": 0}
            value["logit"] = []

        self.save_data(
            filepath=self.UNLABELED_DATA_DIR + "/unlabeledData.json", data=unlabeled_data
        )

    def train_test_val_split(self):
        """Split data into train, test, and validation sets."""
        with open(self.UNLABELED_DATA_DIR + "/unlabeledData.json") as f:
            whole_data = json.load(f)

        unlabel_set = []
        eval_set = []
        valid_set = []
        train_set = []

        train_set_num = int(self.INITIAL_DATA_NUM)
        eval_set_num = int(self.EVAL_DATA_NUM)
        valid_set_num = int(self.EVAL_DATA_NUM)

        if self.SAMPLING_OPTION == "random":
            for _ in tqdm(
                range(train_set_num), desc="unlabeled-train-test split(train)"
            ):
                train_set.append(whole_data.pop(random.randint(0, len(whole_data) - 1)))
            for _ in tqdm(
                range(eval_set_num), desc="unlabeled-train-test split(eval)"
            ):
                eval_set.append(whole_data.pop(random.randint(0, len(whole_data) - 1)))
            for _ in tqdm(
                range(valid_set_num), desc="unlabeled-train-test split(valid)"
            ):
                valid_set.append(whole_data.pop(random.randint(0, len(whole_data) - 1)))
            unlabel_set = whole_data

        elif self.SAMPLING_OPTION == "latin":
            sample_train = self._space_train.latin_sample(
                n_samples=train_set_num
            ).tolist()
            sample_eval = self._space_eval.latin_sample(n_samples=eval_set_num).tolist()
            sample_valid = self._space_valid.latin_sample(
                n_samples=valid_set_num
            ).tolist()
            space_list = list(self.configfile["algorithm"]["prangeDict"].values())
            sample_train = self._normalize(data=sample_train, prange_list=space_list)
            sample_eval = self._normalize(data=sample_eval, prange_list=space_list)
            sample_valid = self._normalize(data=sample_valid, prange_list=space_list)

            for _ in tqdm(range(train_set_num), desc="trainSet"):
                distance_matrix_train = np.zeros((len(whole_data), len(sample_train)))
                for j in range(len(sample_train)):
                    for i in range(len(whole_data)):
                        distance_matrix_train[i][j] = self._calc_euclidean(
                            whole_data[i]["coordination"], sample_train[j]
                        )
                min_idx_train = np.argmin(distance_matrix_train)
                un_train, sam_train = np.unravel_index(
                    min_idx_train, distance_matrix_train.shape
                )
                train_set.append(whole_data.pop(un_train))
                sample_train = np.delete(sample_train, sam_train, axis=0)

            for _ in tqdm(range(eval_set_num), desc="evalSet"):
                distance_matrix_eval = np.zeros((len(whole_data), len(sample_eval)))
                for j in range(len(sample_eval)):
                    for i in range(len(whole_data)):
                        distance_matrix_eval[i][j] = self._calc_euclidean(
                            whole_data[i]["coordination"], sample_eval[j]
                        )
                min_idx_eval = np.argmin(distance_matrix_eval)
                un_eval, sam_eval = np.unravel_index(
                    min_idx_eval, distance_matrix_eval.shape
                )
                eval_set.append(whole_data.pop(un_eval))
                sample_eval = np.delete(sample_eval, sam_eval, axis=0)

            for _ in tqdm(range(valid_set_num), desc="validSet"):
                distance_matrix_valid = np.zeros((len(whole_data), len(sample_valid)))
                for j in range(len(sample_valid)):
                    for i in range(len(whole_data)):
                        distance_matrix_valid[i][j] = self._calc_euclidean(
                            whole_data[i]["coordination"], sample_valid[j]
                        )
                min_idx_valid = np.argmin(distance_matrix_valid)
                un_valid, sam_valid = np.unravel_index(
                    min_idx_valid, distance_matrix_valid.shape
                )
                valid_set.append(whole_data.pop(un_valid))
                sample_valid = np.delete(sample_valid, sam_valid, axis=0)

            unlabel_set = whole_data

        else:
            raise NameError("Please check Sampling Option")

        # Generate CSV files
        valid_df = {parameter: [] for parameter in self.PARAM_NAME}
        eval_df = {parameter: [] for parameter in self.PARAM_NAME}
        train_df = {parameter: [] for parameter in self.PARAM_NAME}

        for idx, value in tqdm(enumerate(valid_set), desc="valid_csv"):
            for num, name in enumerate(self.PARAM_NAME):
                valid_df[name].append(value["coordination"][num])

        for idx, value in tqdm(enumerate(eval_set), desc="eval_csv"):
            for num, name in enumerate(self.PARAM_NAME):
                eval_df[name].append(value["coordination"][num])

        for idx, value in tqdm(enumerate(train_set), desc="train_csv"):
            for num, name in enumerate(self.PARAM_NAME):
                train_df[name].append(value["coordination"][num])

        valid_pd = pd.DataFrame(valid_df)
        eval_pd = pd.DataFrame(eval_df)
        train_pd = pd.DataFrame(train_df)

        valid_pd.to_csv(f"{self.SPLIT_DATA_DIR}/valid.csv", sep=",", index=False)
        eval_pd.to_csv(f"{self.SPLIT_DATA_DIR}/eval.csv", sep=",", index=False)
        train_pd.to_csv(
            f"{self.SPLIT_DATA_DIR}/underLabelingSet.csv", sep=",", index=False
        )

        # Save JSON files
        with open(f"{self.SPLIT_DATA_DIR}/unlabeledSet.json", "w") as f:
            json.dump(unlabel_set, f, indent=4)

        with open(f"{self.SPLIT_DATA_DIR}/underLabelingSet.json", "w") as f:
            json.dump(train_set, f, indent=4)

        with open(f"{self.SPLIT_DATA_DIR}/evalSet.json", "w") as f:
            json.dump(eval_set, f, indent=4)

        with open(f"{self.SPLIT_DATA_DIR}/validSet.json", "w") as f:
            json.dump(valid_set, f, indent=4)


if __name__ == "__main__":
    from distutils.dir_util import copy_tree

    method = ["Random"]
    Smethod = method[0]
    for surface in ["Rosenbrock", "HyperEllipsoid"]:
        for sampling_method in ["random"]:
            for model in ["TabPFN"]:
                for var in [2, 3]:
                    for balance in [50]:
                        for initalsampling_size in [20, 30]:
                            for method in ["Random"]:
                                if var == 2:
                                    dis = 1
                                if var == 3:
                                    dis = 5
                                for idx in range(0, 10):
                                    from_file_path = f"C:\\Users\\user\\Desktop\\RS\\DataSet\\{Smethod}\\Sample_var{var}_{initalsampling_size}\\{idx}"
                                    to_file_path = f"C:\\Users\\user\\Desktop\\RS\\DataSet\\{Smethod}\\{surface}_{sampling_method}_var{var}_dis{dis}_{model}_{initalsampling_size}_{balance}\\{idx}"
                                    copy_tree(from_file_path, to_file_path)
